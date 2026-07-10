"""
Analysis and recommendation endpoints

Updated to support:
- Gap indicators (Fragmentation / Inconsistency / Incompleteness)
- Rule Engine validation verdicts
- Fact Table statistics
- Agent reasoning trace
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from loguru import logger
from typing import List
from pathlib import Path
import asyncio
import uuid
import time
import json
import shutil
from threading import Lock

from ...models.requests import (
    RecommendationRequest,
    GapDetectionRequest,
    ChatRequest,
    MarkedPapersRequest
)
from ..dependencies import (
    get_analysis_context,
    create_ephemeral_analysis_context,
    get_document_processor,
    get_retriever,
    get_glm_interface,
    release_analysis_context,
)
from ...utils.config_loader import get_config
from ...utils.job_store import (
    append_conversation_message,
    clear_conversation,
    get_conversation_messages,
    get_job,
    get_job_events,
    get_job_graph,
    get_latest_completed_job,
    is_cancel_requested,
    record_job_event,
    request_cancel,
    retry_job,
    save_job,
)
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload
from ...services.analysis_queue import get_analysis_queue

router = APIRouter()

_CONVERSATION_LOCKS: dict[str, Lock] = {}
_CONVERSATION_LOCKS_GUARD = Lock()

def _set_analysis_job(job_id: str, **updates):
    job = dict(get_job(job_id) or {})
    job.update(updates)
    save_job(job_id, job)
    return job


@router.post("/analysis-status/{job_id}/cancel")
async def cancel_analysis(job_id: str):
    """Request cooperative cancellation for a queued or running analysis."""
    job = request_cancel(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    record_job_event(job_id, "job.cancel_requested", status=job.get("status"))
    return job


@router.post("/analysis-status/{job_id}/retry")
async def retry_analysis(job_id: str):
    """Queue a failed/cancelled job again using its retained input PDFs."""
    job = retry_job(job_id)
    if job is None:
        raise HTTPException(status_code=409, detail="Job cannot be retried")
    record_job_event(job_id, "job.retry_requested", status="queued")
    get_analysis_queue().notify()
    return job


def _get_analysis_job(job_id: str):
    return get_job(job_id)


class JobCancelled(Exception):
    """Raised between analysis phases after a user requests cancellation."""


def _ensure_job_active(job_id: str) -> None:
    if is_cancel_requested(job_id):
        raise JobCancelled("Analisis dibatalkan oleh pengguna")


def _conversation_lock(conversation_id: str) -> Lock:
    with _CONVERSATION_LOCKS_GUARD:
        return _CONVERSATION_LOCKS.setdefault(conversation_id, Lock())


def _add_uploaded_paper_similarity(papers, vector_store) -> None:
    """Attach each paper's mean semantic similarity to the other uploads.

    The score is deliberately scoped to the current upload set, not the shared
    corpus.  It gives a researcher a quick indication of topical overlap while
    preserving the detailed evidence analysis elsewhere in the result.
    """
    for paper in papers:
        paper["similarity_percent"] = None
    if len(papers) < 2:
        return

    try:
        import numpy as np

        texts = [str(paper.get("content", ""))[:6000] for paper in papers]
        embeddings = np.asarray(
            vector_store.embedding_model.encode(texts, show_progress_bar=False),
            dtype=float,
        )
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.maximum(norms, 1e-12)
        similarity_matrix = normalized @ normalized.T
        for index, paper in enumerate(papers):
            other_scores = np.delete(similarity_matrix[index], index)
            average = float(np.clip(other_scores.mean(), 0.0, 1.0))
            paper["similarity_percent"] = round(average * 100)
    except Exception as exc:
        logger.warning(f"Could not calculate uploaded-paper similarity: {exc}")


def translate_to_indonesian(glm, text):
    """Translate text to Indonesian using LLM"""
    if not text:
        return text
    
    if isinstance(text, list):
        # Translate list items
        translated = []
        for item in text:
            prompt = f"""Translate the following text to Indonesian. Keep technical terms if they don't have good Indonesian equivalents.

Text: {item}

Indonesian translation:"""
            result = glm.generate(prompt, max_tokens=500)
            translated.append(result.strip())
        return translated
    else:
        # Translate single text
        prompt = f"""Translate the following text to Indonesian. Keep technical terms if they don't have good Indonesian equivalents.

Text: {text}

Indonesian translation:"""
        result = glm.generate(prompt, max_tokens=1000)
        return result.strip()


@router.post("/recommend")
def recommend(request: RecommendationRequest):
    """Get research recommendations via the agentic pipeline.

    Sync endpoint (runs in threadpool) — the LLM call blocks for tens of
    seconds and must not run on the event loop.
    """
    try:
        analysis_context = create_ephemeral_analysis_context()
        coordinator = analysis_context.coordinator
        
        # Process through multi-agent system
        results = coordinator.process_research_query(
            query=request.query,
            context=request.user_context or {}
        )
        
        # Build structured gap indicators
        raw_indicators = results.get("gap_indicators", [])
        gap_indicators = []
        for gi in raw_indicators:
            try:
                gap_indicators.append({
                    "indicator_type": gi.get("type", gi.get("indicator_type", "FRAGMENTATION")),
                    "title": gi.get("title", ""),
                    "description": gi.get("description", ""),
                    "confidence": gi.get("confidence", 0.0),
                    "adjusted_confidence": gi.get("adjusted_confidence"),
                    "rule_engine_verdict": gi.get("rule_engine_verdict"),
                    "requires_human_validation": gi.get("requires_human_validation", True),
                    "evidence": gi.get("evidence", []),
                    "supporting_papers": gi.get("supporting_papers", []),
                    "suggested_directions": gi.get("suggested_directions", []),
                })
            except Exception:
                pass  # Skip malformed indicators
        
        return {
            "query": request.query,
            "execution_mode": results.get("execution_mode", "sequential"),
            "gap_indicators": gap_indicators,
            "total_indicators": len(gap_indicators),
            "rule_engine_report": results.get("rule_engine_report", {}),
            "fact_table_stats": results.get("fact_table_stats", {}),
            "recommendations": results.get("recommendations", []),
            "reasoning_trace": results.get("reasoning_trace", []),
            "self_critique": results.get("self_critique", {}),
            "analysis": results.get("analysis", {}),
            "metadata": results.get("metadata", {}),
        }
    except Exception as e:
        logger.error(f"Recommendation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gaps")
def detect_gaps(request: GapDetectionRequest):
    """Detect synthesis gaps using the 3-indicator model (sync → threadpool)"""
    try:
        analysis_context = create_ephemeral_analysis_context()
        gap_analyzer = analysis_context.gap_analyzer
        retriever = analysis_context.retriever
        
        # Get relevant papers
        results = retriever.retrieve(query=request.topic, top_k=20)
        papers = [
            {
                "content": r.document.content,
                "metadata": r.document.metadata
            }
            for r in results
        ]
        
        # Analyze gaps
        gaps = gap_analyzer.analyze_gaps(
            topic=request.topic,
            papers=papers,
            depth=request.depth
        )
        
        # Build response with indicator structure
        gap_indicators = []
        for gap in gaps:
            indicator = {
                "indicator_type": getattr(gap, "indicator_type", 
                                   getattr(gap, "gap_type", "FRAGMENTATION")),
                "description": getattr(gap, "description", str(gap)),
                "confidence": getattr(gap, "confidence", 0.0),
                "rule_engine_verdict": getattr(gap, "rule_engine_verdict", None),
                "requires_human_validation": getattr(
                    gap, "requires_human_validation", True
                ),
                "suggested_directions": getattr(gap, "suggested_directions", []),
                "evidence": getattr(gap, "evidence", []),
            }
            gap_indicators.append(indicator)
        
        # Get rule engine stats if available
        rule_report = {}
        try:
            rule_engine = analysis_context.rule_engine
            if rule_engine:
                pass_count = sum(
                    1 for g in gap_indicators
                    if g.get("rule_engine_verdict") == "PASS"
                )
                flag_count = sum(
                    1 for g in gap_indicators
                    if g.get("rule_engine_verdict") == "FLAG"
                )
                reject_count = sum(
                    1 for g in gap_indicators
                    if g.get("rule_engine_verdict") == "REJECT"
                )
                rule_report = {
                    "total": len(gap_indicators),
                    "passed": pass_count,
                    "flagged": flag_count,
                    "rejected": reject_count,
                }
        except Exception:
            pass
        
        # Get fact table stats
        ft_stats = {}
        try:
            fact_table = analysis_context.fact_table
            if fact_table:
                ft_stats = fact_table.get_statistics()
        except Exception:
            pass
        
        return {
            "topic": request.topic,
            "total_indicators": len(gap_indicators),
            "gap_indicators": gap_indicators,
            "rule_engine_report": rule_report,
            "fact_table_stats": ft_stats,
            # Legacy field (backward compat)
            "total_gaps": len(gap_indicators),
            "gaps": [
                {
                    "type": g.get("indicator_type", "UNKNOWN"),
                    "description": g.get("description", ""),
                    "confidence": g.get("confidence", 0.0),
                    "suggested_directions": g.get("suggested_directions", []),
                }
                for g in gap_indicators
            ],
        }
    except Exception as e:
        logger.error(f"Gap detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
def chat(request: ChatRequest):
    """Chat with a durable, isolated research-assistant conversation."""
    try:
        glm = get_glm_interface()
        conversation_id = getattr(request, "conversation_id", None) or str(uuid.uuid4())
        message = request.message.strip()
        if not message:
            raise HTTPException(status_code=400, detail="Pesan tidak boleh kosong")
        if len(message) > 8000:
            raise HTTPException(status_code=422, detail="Pesan maksimal 8000 karakter")

        with _conversation_lock(conversation_id):
            history = get_conversation_messages(conversation_id, limit=10)
            append_conversation_message(conversation_id, "user", message)
            response = glm.chat(
                message=message,
                use_history=request.use_history,
                history=history,
            )
            append_conversation_message(conversation_id, "assistant", response)

            # Chat intentionally searches the explicitly shared research corpus.
            sources = []
            try:
                retriever = get_retriever()
                results = retriever.retrieve(query=message, top_k=3)
                sources = [
                    r.document.metadata.get("title", r.document.metadata.get("source", ""))
                    for r in results if r.document.metadata
                ]
            except Exception as exc:
                logger.warning(f"Chat source retrieval unavailable: {exc}")
        
        return {
            "message": message,
            "response": response,
            "conversation_id": conversation_id,
            "sources": sources,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/chat/{conversation_id}")
def reset_chat(conversation_id: str):
    """Delete only the requested durable chat session."""
    deleted = clear_conversation(conversation_id)
    with _CONVERSATION_LOCKS_GUARD:
        _CONVERSATION_LOCKS.pop(conversation_id, None)
    return {"success": True, "deleted": deleted, "conversation_id": conversation_id}


def _parse_selection_json(raw: str) -> dict:
    """Parse grounded JSON output for the marked-papers analysis."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('{'):
        match = _re.search(r'(\{.*\})', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        data = _json.loads(text)
        if isinstance(data, dict):
            sugg = []
            for s in data.get("suggestions", []):
                if isinstance(s, dict):
                    raw_sources = s.get("source_papers", s.get("supporting_papers", s.get("papers", [])))
                    if isinstance(raw_sources, str):
                        raw_sources = [raw_sources]
                    sugg.append({
                        "title": str(s.get("title", s.get("judul", ""))).strip(),
                        "rationale": str(s.get("rationale", s.get("alasan", ""))).strip(),
                        "basis": str(s.get("basis", s.get("evidence", s.get("bukti", "")))).strip(),
                        "source_papers": [str(p).strip() for p in raw_sources if str(p).strip()][:5] if isinstance(raw_sources, list) else [],
                        "gap_type": str(s.get("gap_type", "")).strip().upper(),
                    })
                elif isinstance(s, str):
                    sugg.append({"title": s, "rationale": "", "basis": "", "source_papers": [], "gap_type": ""})
            return {
                "common_keywords": [str(k) for k in data.get("common_keywords", data.get("kata_kunci", []))],
                "shared_themes": [str(t) for t in data.get("shared_themes", data.get("tema", []))],
                "suggestions": sugg,
                "summary": data.get("summary", data.get("ringkasan", "")),
            }
    except (_json.JSONDecodeError, ValueError):
        pass
    return {"common_keywords": [], "shared_themes": [], "suggestions": [], "summary": text[:500]}


def _ground_selection_suggestions(suggestions: list, papers: list[dict]) -> list[dict]:
    """Keep only research directions tied to at least two marked papers.

    The marked-paper flow receives abstracts rather than full text.  Requiring
    cited titles prevents generic algorithm/domain combinations from being
    presented as evidence-backed synthesis opportunities.
    """
    known_titles = [str(p.get("title", "")).strip() for p in papers if p.get("title")]

    def _normalise(title: str) -> str:
        import re
        return re.sub(r"\s+", " ", title.lower()).strip()

    def _match_title(candidate: str) -> str | None:
        candidate_norm = _normalise(candidate)
        if not candidate_norm:
            return None
        for title in known_titles:
            title_norm = _normalise(title)
            if candidate_norm == title_norm or candidate_norm in title_norm or title_norm in candidate_norm:
                return title
        return None

    grounded = []
    for suggestion in suggestions:
        if not isinstance(suggestion, dict) or not suggestion.get("title"):
            continue
        sources = []
        for source in suggestion.get("source_papers", []):
            matched = _match_title(str(source))
            if matched and matched not in sources:
                sources.append(matched)
        if len(sources) < 2:
            continue
        suggestion["source_papers"] = sources
        suggestion["basis"] = str(suggestion.get("basis", "")).strip()
        grounded.append(suggestion)
    return grounded[:3]


def _parse_weaknesses_json(raw: str) -> dict:
    """Parse LLM JSON output for per-paper weaknesses (tersurat & tersirat)."""
    import json as _json
    import re as _re
    text = (raw or "").strip()
    match = _re.search(r'```(?:json)?\s*(\{.*\})\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('{'):
        match = _re.search(r'(\{.*\})', text, _re.DOTALL)
        if match:
            text = match.group(1)

    def _clean(items):
        """Normalise weakness items to {poin, dasar, kutipan} (handles legacy strings)."""
        out = []
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                poin = str(
                    it.get("poin", it.get("point", it.get("kelemahan", it.get("kekurangan", ""))))
                ).strip().lstrip('-•* ').strip()
                dasar = str(
                    it.get("dasar", it.get("basis", it.get("alasan", it.get("bukti", ""))))
                ).strip()
                kutipan = str(
                    it.get("kutipan", it.get("quote", it.get("kutipan_verbatim", "")))
                ).strip().strip('"').strip()
                if poin:
                    out.append({"poin": poin, "dasar": dasar, "kutipan": kutipan})
            else:
                s = str(it).strip().lstrip('-•* ').strip()
                if s:
                    out.append({"poin": s, "dasar": "", "kutipan": ""})
        return out[:3]

    try:
        data = _json.loads(text)
        if isinstance(data, dict):
            return {
                "tersurat": _clean(data.get("tersurat", data.get("explicit", []))),
                "tersirat": _clean(data.get("tersirat", data.get("implicit", []))),
            }
    except (_json.JSONDecodeError, ValueError):
        pass
    return {"tersurat": [], "tersirat": []}


def _normalize_text(s: str) -> str:
    """Lowercase + collapse whitespace for robust substring matching."""
    import re as _re
    return _re.sub(r"\s+", " ", (s or "").lower()).strip()


def _fuzzy_contains(needle: str, haystack: str, threshold: float = 0.82) -> float:
    """
    Return best similarity (0-1) of `needle` against any same-length window of
    `haystack`. Cheap anti-hallucination check for verbatim-ish quotes.
    """
    from difflib import SequenceMatcher
    needle = _normalize_text(needle)
    haystack = _normalize_text(haystack)
    if not needle or not haystack:
        return 0.0
    if needle in haystack:
        return 1.0
    # Slide a window the size of the needle across the haystack (word-stepped).
    nlen = len(needle)
    best = 0.0
    step = max(1, nlen // 2)
    for start in range(0, max(1, len(haystack) - nlen + 1), step):
        window = haystack[start:start + nlen]
        ratio = SequenceMatcher(None, needle, window).ratio()
        if ratio > best:
            best = ratio
            if best >= 0.97:
                break
    return best


def _content_word_overlap(claim: str, full_norm: str) -> float:
    """Fraction of meaningful words in `claim` that also appear in the paper."""
    import re as _re
    stop = {
        "yang", "dan", "atau", "tidak", "ada", "pada", "ini", "itu", "untuk",
        "dengan", "dari", "ke", "di", "the", "a", "an", "of", "to", "in", "is",
        "are", "and", "or", "not", "no", "this", "that", "study", "paper",
        "jurnal", "penelitian", "hanya", "secara", "sebuah", "adalah",
    }
    words = [w for w in _re.findall(r"[a-zA-Z]{4,}", claim.lower()) if w not in stop]
    if not words:
        return 0.0
    hits = sum(1 for w in set(words) if w in full_norm)
    return hits / len(set(words))


def _verify_paper_weaknesses(
    parsed,
    full_content,
    source_name="",
    vector_store=None,
    analysis_job_id="",
):
    """
    Verify each weakness point against the paper text so the output is grounded,
    not guessed.

    - tersurat (explicit): the 'kutipan'/'dasar' MUST be locatable in the paper
      (substring or fuzzy match). Unverifiable points are DROPPED — they are
      likely hallucinations. Verified points get verification_status='terverifikasi'.
    - tersirat (implicit, by definition not written): grounded against the paper
      via the project's own vector store (embedding similarity, filtered to this
      source) with a content-word overlap fallback. Points with no grounding at
      all are dropped; the rest carry verification_status + confidence.
    """
    full_norm = _normalize_text(full_content)

    def _ground_score(text: str) -> float:
        # Primary: reuse the project's embeddings via the vector store.
        if vector_store is not None and source_name and text:
            try:
                source_filter = {"source": source_name}
                if analysis_job_id:
                    source_filter = {
                        "$and": [
                            {"analysis_job_id": analysis_job_id},
                            source_filter,
                        ]
                    }
                results = vector_store.search(query=text, top_k=1, filter_metadata=source_filter)
                if results:
                    return max(0.0, float(results[0].score))
            except Exception as e:
                logger.debug(f"Weakness grounding search failed: {e}")
        # Fallback: lexical overlap with the paper text.
        return _content_word_overlap(text, full_norm)

    verified_tersurat = []
    for item in parsed.get("tersurat", []):
        quote = item.get("kutipan") or item.get("dasar") or item.get("poin")
        match = _fuzzy_contains(quote, full_content)
        if match >= 0.82:
            item["verification_status"] = "terverifikasi"
            item["confidence"] = round(match, 2)
            verified_tersurat.append(item)
        # else: explicit claim we cannot find in the text → drop (hallucination)

    verified_tersirat = []
    for item in parsed.get("tersirat", []):
        basis = item.get("dasar") or item.get("poin")
        score = _ground_score(basis)
        if score < 0.2:
            continue  # ungrounded inference → drop
        item["verification_status"] = "terbukti" if score >= 0.5 else "inferensi"
        item["confidence"] = round(score, 2)
        verified_tersirat.append(item)

    return {"tersurat": verified_tersurat, "tersirat": verified_tersirat}


@router.post("/analyze-selection")
async def analyze_selection(request: MarkedPapersRequest):
    """
    Analyze a small set of user-marked papers: find shared keywords/themes
    and suggest new research directions. Designed for the 'mark 3-5 papers' flow.
    """
    papers = request.papers or []
    if len(papers) < 2:
        raise HTTPException(status_code=400, detail="Tandai minimal 2 paper (disarankan 3-5).")

    try:
        glm = get_glm_interface()

        paper_block = "\n\n".join([
            f"Paper {i + 1}:\n"
            f"Judul: {p.get('title', 'Tanpa Judul')}\n"
            f"Tahun: {p.get('year', '-')}\n"
            f"Abstrak: {str(p.get('abstract', '') or '')[:800]}"
            for i, p in enumerate(papers)
        ])

        topic_line = f"Topik/kata kunci pencarian awal: {request.query}\n\n" if request.query else ""

        prompt = (
            "Anda adalah asisten peneliti yang sangat ketat terhadap bukti. Pengguna telah menandai beberapa paper. "
            "Analisis HANYA berdasarkan judul, tahun, dan abstrak yang diberikan; jangan menambahkan metode, hasil, "
            "dataset, atau konteks yang tidak tertulis. Gunakan Bahasa Indonesia.\n\n"
            f"{topic_line}{paper_block}\n\n"
            "Tugas:\n"
            "1. common_keywords: 3-5 kata kunci/konsep yang BENAR-BENAR muncul atau jelas tersirat pada minimal dua paper.\n"
            "2. shared_themes: 1-3 tema bersama yang didukung minimal dua paper.\n"
            "3. suggestions: maksimal 3 arah penelitian. HANYA buat saran jika ada hubungan/kontras nyata antar minimal dua paper. "
            "JANGAN membuat saran sekadar menggabungkan nama algoritma + domain, dan JANGAN mengubah setiap kata kunci menjadi proposal baru. "
            "Jika bukti tidak cukup, kembalikan suggestions sebagai array kosong.\n"
            "4. Untuk setiap suggestion WAJIB isi: title (spesifik), rationale (mengapa hubungan/kontras paper menciptakan peluang), "
            "basis (bukti ringkas dari abstrak), source_papers (tepat dua atau lebih judul paper dari input), dan gap_type "
            "(FRAGMENTATION, INCONSISTENCY, atau INCOMPLETENESS).\n"
            "5. summary: ringkasan 1-2 kalimat.\n\n"
            "Kembalikan HANYA JSON (tanpa teks lain) dengan struktur: "
            '{"common_keywords": [...], "shared_themes": [...], '
            '"suggestions": [{"title": "...", "rationale": "...", "basis": "...", '
            '"source_papers": ["judul persis dari input", "judul persis dari input"], "gap_type": "FRAGMENTATION"}], '
            '"summary": "..."}'
        )

        raw = glm.generate(prompt, max_tokens=1000, format="json")
        result = _parse_selection_json(raw if isinstance(raw, str) else str(raw))
        result["suggestions"] = _ground_selection_suggestions(result["suggestions"], papers)
        result["suggestion_note"] = (
            "Hanya arah penelitian yang ditautkan ke minimal dua paper bertanda yang ditampilkan."
        )
        result["paper_count"] = len(papers)
        result["papers"] = [p.get("title", "Tanpa Judul") for p in papers]
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Selection analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload-and-analyze")
async def upload_and_analyze(
    files: List[UploadFile] = File(...)
):
    """
    Upload PDFs and automatically analyze them.
    Returns job_id to track progress.
    """
    input_paths: list[Path] = []
    job_dir: Path | None = None
    try:
        config = get_config()
        allowed_types = {str(t).lower().lstrip(".") for t in config.data.allowed_file_types}
        if "pdf" not in allowed_types:
            raise HTTPException(status_code=415, detail="PDF uploads are not enabled")
        job_id = str(uuid.uuid4())
        job_dir = Path(config.data.raw_path) / "analysis_jobs" / job_id
        job_dir.mkdir(parents=True, exist_ok=False)

        # Inputs are retained in a per-job directory until retention cleanup so
        # a durable queue can retry after a process restart.
        files_metadata = []
        for index, file in enumerate(files):
            safe_name = sanitize_filename(file.filename)
            input_path = job_dir / f"{index:02d}_{safe_name}"
            await write_validated_pdf_upload(file, input_path, config.data.max_file_size_mb)
            input_paths.append(input_path)
            files_metadata.append({"name": safe_name})

        # Persist a queued job before signalling the local worker.  The payload
        # contains only local paths/filenames, never document content.
        _set_analysis_job(
            job_id,
            status="queued",
            progress=0,
            message="Menunggu worker analisis...",
            results=None,
            error=None,
            created_at=time.time(),
            max_attempts=config.queue.max_attempts,
            payload={
                "pdf_paths": [str(path) for path in input_paths],
                "input_dir": str(job_dir),
                "files": files_metadata,
            },
        )
        record_job_event(job_id, "job.created", status="queued", data={"file_count": len(input_paths)})
        get_analysis_queue().notify()
        
        return {
            "success": True,
            "job_id": job_id,
            "files_count": len(files),
            "message": "Analysis queued. Use /api/analysis-status/{job_id} to check progress."
        }
    
    except HTTPException:
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as e:
        if job_dir:
            shutil.rmtree(job_dir, ignore_errors=True)
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-status/{job_id}")
async def get_analysis_status(job_id: str, lang: str = "en"):
    """Get the status of an analysis job
    
    Args:
        job_id: The job ID
        lang: Language for results (en/id). Default: en
    """
    job = _get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Completed jobs already persist their isolated fact-table stats.  Never
    # consult the global singleton here: it can belong to another job.
    if job["status"] == "completed" and job.get("results"):
        results = job["results"]
        result_changed = False
        
        # Add rule_engine_report if not present
        if "rule_engine_report" not in results:
            results["rule_engine_report"] = {}
            result_changed = True
        
        if "fact_table_stats" not in results:
            results["fact_table_stats"] = {}
            result_changed = True
        
        # Add reasoning_trace placeholder
        if "reasoning_trace" not in results:
            results["reasoning_trace"] = []
            result_changed = True
        if result_changed:
            job["results"] = results
            _set_analysis_job(job_id, **job)
    
    # Translate if requested and job is completed
    if lang == "id" and job["status"] == "completed" and "results" in job:
        if "results_id" not in job:
            glm = get_glm_interface()
            results = job["results"]
            
            # Translate structured fields
            translated_gaps = []
            for g in results.get("gaps", []):
                if isinstance(g, dict):
                    tg = dict(g)
                    tg["title"] = translate_to_indonesian(glm, g.get("title", ""))
                    tg["description"] = translate_to_indonesian(glm, g.get("description", ""))
                    translated_gaps.append(tg)
                else:
                    translated_gaps.append(g)

            translated_recs = []
            for r in results.get("recommendations", []):
                if isinstance(r, dict):
                    tr = dict(r)
                    for key in ("title", "description", "why", "how"):
                        if tr.get(key):
                            tr[key] = translate_to_indonesian(glm, tr[key])
                    translated_recs.append(tr)
                else:
                    translated_recs.append(r)

            translated_roadmap = []
            for phase in results.get("roadmap", []):
                if isinstance(phase, dict):
                    tp = dict(phase)
                    tp["phase"] = translate_to_indonesian(glm, phase.get("phase", ""))
                    tp["items"] = translate_to_indonesian(glm, phase.get("items", []))
                    translated_roadmap.append(tp)
                else:
                    translated_roadmap.append(phase)

            job["results_id"] = {
                **results,
                "topics": translate_to_indonesian(glm, results.get("topics", [])),
                "summary": translate_to_indonesian(glm, results.get("summary", "")),
                "gaps": translated_gaps,
                "recommendations": translated_recs,
                "roadmap": translated_roadmap,
            }
            _set_analysis_job(job_id, **job)
        
        return {
            **job,
            "results": job["results_id"]
        }
    
    return job


# ── Helper parsers for LLM fallback output ──────────────────────────────────

def _parse_gap_json(raw: str) -> list:
    """Parse LLM JSON output for gaps. Falls back to text parsing."""
    import json as _json
    import re as _re
    text = raw.strip()
    # Try to extract JSON array from markdown code blocks
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        # Try to find a JSON array anywhere in the text
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "title": item.get("title", item.get("gap", "Untitled")),
                        "description": item.get("description", ""),
                        "type": item.get("type", "general"),
                        "confidence": item.get("confidence", 0.5),
                        "evidence": item.get("evidence", []),
                        "suggested_directions": item.get("suggested_directions", []),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    # Fallback: parse numbered list text
    return _parse_gap_text(text)


def _parse_gap_text(text: str) -> list:
    """Parse plain text gaps (numbered list) into structured dicts."""
    import re as _re
    gaps = []
    # Split by numbered items like "1." or "- "
    items = _re.split(r'\n\s*(?:\d+[\.\)]\s*|-\s+)', text)
    for item in items:
        item = item.strip()
        if not item or len(item) < 10:
            continue
        title = item.split('\n')[0].strip().rstrip(':')
        desc = '\n'.join(item.split('\n')[1:]).strip() or title
        gaps.append({
            "title": title[:200],
            "description": desc,
            "type": "general",
            "confidence": 0.5,
            "evidence": [],
            "suggested_directions": [],
        })
    return gaps


def _coerce_rec_dict(item: dict, idx: int) -> dict:
    """Normalise one LLM dict into a recommendation record (or {} if degenerate)."""
    title = _clean_rec_field(str(item.get("title", "")))
    description = _clean_rec_field(str(item.get("description", "")))
    if _is_degenerate_text(title) and _is_degenerate_text(description):
        return {}
    default_priority = "high" if idx < 2 else "medium" if idx < 4 else "low"
    return {
        "title": title or "Usulan penelitian",
        "description": description,
        "gap_type": str(item.get("gap_type", item.get("type", ""))).upper(),
        "why": _clean_rec_field(str(item.get("why", ""))),
        "how": _clean_rec_field(str(item.get("how", ""))),
        "priority": item.get("priority", default_priority),
    }


def _parse_recommendations_json(raw: str) -> list:
    """
    Parse LLM JSON output for recommendations. Robust to:
    - a JSON array  [ {...}, {...} ]
    - a SINGLE JSON object  {...}  (small models often drop the array wrapper)
    - several bare objects  {...}\n{...}  not wrapped in an array
    - markdown code fences around any of the above
    Never lets raw JSON leak into a recommendation field.
    """
    import json as _json
    import re as _re
    text = (raw or "").strip()

    # Unwrap a ```json ... ``` fence if present.
    fence = _re.search(r'```(?:json)?\s*(.+?)\s*```', text, _re.DOTALL)
    if fence:
        text = fence.group(1).strip()

    parsed = None
    # 1) Try the whole payload as-is (handles both array and single object).
    try:
        parsed = _json.loads(text)
    except (_json.JSONDecodeError, ValueError):
        parsed = None

    # 2) If that failed, try to isolate a top-level array.
    if parsed is None:
        m = _re.search(r'\[.*\]', text, _re.DOTALL)
        if m:
            try:
                parsed = _json.loads(m.group())
            except (_json.JSONDecodeError, ValueError):
                parsed = None

    # 3) Still nothing → collect every individual {...} object and parse each.
    if parsed is None:
        objs = []
        for m in _re.finditer(r'\{[^{}]*\}', text, _re.DOTALL):
            try:
                objs.append(_json.loads(m.group()))
            except (_json.JSONDecodeError, ValueError):
                continue
        if objs:
            parsed = objs

    # Normalise the shape to a list of dicts.
    if isinstance(parsed, dict):
        parsed = [parsed]
    if isinstance(parsed, list):
        result = []
        for idx, item in enumerate(parsed):
            if isinstance(item, dict):
                rec = _coerce_rec_dict(item, idx)
                if rec:
                    result.append(rec)
        if result:
            return result

    # Last resort: plain-text parsing (guards against raw JSON leakage).
    return _parse_recommendations_text(text)


def _parse_recommendations_text(text: str) -> list:
    """Parse plain text recommendations into structured dicts."""
    import re as _re
    # Safety: if the text still looks like JSON, do NOT dump it into a card.
    stripped = (text or "").strip()
    if stripped.startswith('{') or stripped.startswith('['):
        return []
    recs = []
    items = _re.split(r'\n\s*(?:\d+[\.\)]\s*|-\s+)', text)
    for item in items:
        item = item.strip()
        if not item or len(item) < 10:
            continue
        # Skip any fragment that is (or starts as) raw JSON.
        if item.startswith('{') or item.startswith('['):
            continue
        title = item.split('\n')[0].strip().rstrip(':')
        desc = '\n'.join(item.split('\n')[1:]).strip() or title
        # Skip bare gap-type tags like "[INCOMPLETENESS]".
        if _is_degenerate_text(title) and _is_degenerate_text(desc):
            continue
        recs.append({
            "title": title[:200],
            "description": desc,
            "why": "",
            "how": "",
            "priority": "medium",
        })
    return recs


def _is_degenerate_text(s: str) -> bool:
    """True if a string is just a bare gap-type tag / placeholder (e.g. "[INCOMPLETENESS]")."""
    import re as _re
    t = (s or "").strip()
    if len(t) < 6:
        return True
    return bool(_re.match(
        r'^\[?\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS|UNKNOWN|NULL|N/?A|NONE)\s*\]?$',
        t, _re.IGNORECASE,
    ))


def _clean_rec_field(s: str) -> str:
    """Strip a leading bare gap-type tag like "[INCOMPLETENESS] " from a field."""
    import re as _re
    return _re.sub(
        r'^\s*\[\s*(FRAGMENTATION|INCONSISTENCY|INCOMPLETENESS|UNKNOWN)\s*\]\s*',
        '', (s or ''), flags=_re.IGNORECASE,
    ).strip()


def _build_recommendations_from_gaps(gaps: list) -> list:
    """
    Deterministic fallback: synthesise gap-anchored research proposals directly
    from detected gap indicators. Used when the LLM proposal output is empty or
    degenerate (small models sometimes just echo "[INCOMPLETENESS]"). Keeps the
    output anchored to the Cooper/Booth indicators without another LLM round-trip.
    """
    type_meta = {
        "FRAGMENTATION": {
            "verb": "Mengintegrasikan",
            "why": "Menjawab indikator fragmentasi: jurnal membahas fenomena serupa dari sudut berbeda tetapi belum saling terintegrasi.",
        },
        "INCONSISTENCY": {
            "verb": "Merekonsiliasi",
            "why": "Menjawab indikator inkonsistensi: terdapat temuan antar-jurnal yang saling bertentangan dan belum direkonsiliasi.",
        },
        "INCOMPLETENESS": {
            "verb": "Melengkapi",
            "why": "Menjawab indikator ketidaklengkapan kolektif: ada aspek penting yang belum dicakup bersama oleh jurnal-jurnal yang dianalisis.",
        },
    }
    recs = []
    for idx, g in enumerate(gaps[:5]):
        gtype = str(g.get("type") or "INCOMPLETENESS").upper()
        meta = type_meta.get(gtype, type_meta["INCOMPLETENESS"])
        dirs = [
            str(d).replace("Investigate:", "").strip().rstrip(".")
            for d in (g.get("suggested_directions") or [])
            if str(d).strip()
        ]
        focus = dirs[0] if dirs else (g.get("title") or "")
        if focus:
            title = f"{meta['verb']} aspek: {focus}"[:200]
            desc = (
                f"Penelitian yang {meta['verb'].lower()} {focus[0].lower() + focus[1:] if focus else focus} "
                f"berdasarkan jurnal-jurnal yang dianalisis."
            )
        else:
            title = f"{meta['verb']} literatur pada topik ini"
            desc = g.get("description", "")
        how = ""
        if len(dirs) > 1:
            how = "Tinjau dan bandingkan secara sistematis: " + "; ".join(dirs[:3]) + "."
        recs.append({
            "title": title,
            "description": desc,
            "gap_type": gtype,
            "why": meta["why"],
            "how": how,
            "priority": "high" if idx < 2 else "medium" if idx < 4 else "low",
        })
    return recs


def _parse_paper_groups_json(raw: str) -> list:
    """Parse LLM JSON output classifying each paper by its basis/approach."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "title": item.get("title", item.get("paper", "")),
                        "basis": item.get("basis", item.get("category", "Lainnya")),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    return []


def _parse_roadmap_json(raw: str) -> list:
    """Parse LLM JSON output for roadmap phases."""
    import json as _json
    import re as _re
    text = raw.strip()
    match = _re.search(r'```(?:json)?\s*(\[.*?\])\s*```', text, _re.DOTALL)
    if match:
        text = match.group(1)
    elif not text.startswith('['):
        match = _re.search(r'(\[.*\])', text, _re.DOTALL)
        if match:
            text = match.group(1)
    try:
        items = _json.loads(text)
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "phase": item.get("phase", f"Phase {len(result)+1}"),
                        "items": item.get("items", item.get("tasks", [])),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    # Fallback: parse text roadmap
    return _parse_roadmap_text(text)


def _parse_roadmap_text(text: str) -> list:
    """Parse plain text roadmap into structured phases (robust fallback)."""
    import re as _re
    # Strip stray markdown bold/italic markers that LLMs often leave behind
    text = text.replace('**', '').replace('__', '')
    phases = []
    # Match phase headers AND capture the phase title after it:
    #   "Fase 1: Penelitian Teori", "Phase 2 - Build", "Tahap 3 Pengujian"
    pattern = _re.compile(
        r'(?:^|\n)\s*(?:#{1,3}\s*)?(?:Phase|Fase|Tahap)\s*\d+\s*[:\-.]?\s*([^\n]*)',
        _re.IGNORECASE,
    )
    matches = list(pattern.finditer(text))
    if matches:
        for i, m in enumerate(matches):
            title = m.group(1).strip().rstrip(':').strip()
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            body = text[start:end]
            items = []
            for line in body.split('\n'):
                line = line.strip().lstrip('-•* ').strip()
                line = _re.sub(r'^\d+[.)]\s*', '', line)
                if line and len(line) > 3:
                    items.append(line)
            label = title if title else f"Tahap {len(phases) + 1}"
            if items:
                phases.append({"phase": label, "items": items})
        if phases:
            return phases
    # No phase headers: treat as a flat numbered/bulleted list, dropping preamble
    items = []
    for line in text.split('\n'):
        line = line.strip().lstrip('-•* ').strip()
        line = _re.sub(r'^\d+[.)]\s*', '', line)
        low = line.lower()
        if line and len(line) > 3 and not low.startswith(('berikut', 'peta jalan', 'here', 'roadmap')):
            items.append(line)
    if items:
        return [{"phase": "Rencana Penelitian", "items": items}]
    return []


def process_auto_analysis(job_id: str, pdf_paths: List[Path] | None = None):
    """Run one durable job with an isolated context and scoped retrieval.

    The local queue calls this synchronous function from its worker pool.  It
    intentionally does not run on FastAPI's event loop.  ``pdf_paths`` remains
    optional for legacy/manual callers; durable queue workers load it from the
    persisted job payload.
    """
    try:
        job = _get_analysis_job(job_id)
        if job is None:
            raise RuntimeError("Analysis job not found")
        if pdf_paths is None:
            pdf_paths = [Path(path) for path in (job.get("payload") or {}).get("pdf_paths", [])]
        if not pdf_paths or any(not path.exists() for path in pdf_paths):
            raise FileNotFoundError("Input PDF for this analysis job is unavailable")

        _ensure_job_active(job_id)
        _set_analysis_job(job_id, status="running", progress=5, message="Processing PDFs...")
        record_job_event(job_id, "phase.started", phase="ingestion", status="running")

        analysis_context = get_analysis_context(job_id)
        vector_store = analysis_context.vector_store
        document_processor = get_document_processor()
        glm = analysis_context.llm

        # Retries must not reuse partial chunks from an earlier worker attempt.
        vector_store.delete_by_metadata({"analysis_job_id": job_id})

        # ── Step 1: Ingest PDFs into vector store ──────────────
        total_chunks = 0
        paper_contents = []
        new_papers = 0
        duplicate_papers = 0
        for i, pdf_path in enumerate(pdf_paths):
            _ensure_job_active(job_id)
            # Inputs are stored as "{index}_{original-name}" in their job directory.
            source_name = pdf_path.name.split('_', 1)[-1]
            _set_analysis_job(
                job_id,
                message=f"Processing {source_name}...",
                progress=5 + (i / len(pdf_paths)) * 15,
            )

            processed_doc = document_processor.process_pdf(str(pdf_path))
            # Each analysis is intentionally scoped to its own source chunks.
            # Re-ingesting an identical filename is preferable to leaking data
            # from an earlier job through the shared corpus.
            already_indexed = False
            for chunk in processed_doc.chunks:
                metadata = {
                    "analysis_job_id": job_id,
                    "source": source_name,
                    "title": processed_doc.title or source_name,
                    "chunk_index": chunk.chunk_index,
                }
                if processed_doc.metadata.get("year"):
                    metadata["year"] = int(processed_doc.metadata["year"])
                section = chunk.metadata.get("section") if chunk.metadata else None
                if section:
                    metadata["section"] = section
                vector_store.add_document(chunk.content, metadata)
                total_chunks += 1
            new_papers += 1

            paper_contents.append({
                "source": source_name,
                "title": processed_doc.title or source_name,
                "year": processed_doc.metadata.get("year"),
                "content": " ".join(c.content for c in processed_doc.chunks[:10]),
                "full_content": processed_doc.content or " ".join(
                    c.content for c in processed_doc.chunks
                ),
                "weakness_context": document_processor.extract_weakness_sections(
                    processed_doc.content or " ".join(
                        c.content for c in processed_doc.chunks
                    )
                ),
                "already_indexed": already_indexed,
            })

            _add_uploaded_paper_similarity(paper_contents, vector_store)

        record_job_event(
            job_id,
            "phase.completed",
            phase="ingestion",
            status="running",
            data={"files_processed": len(paper_contents), "chunks": total_chunks},
        )

        _set_analysis_job(job_id, progress=20, message="Extracting topics...")
        _ensure_job_active(job_id)

        # ── Step 2: Extract topics from UPLOADED papers only ────
        sample_text = " ".join([p["content"] for p in paper_contents])

        topic_prompt = f"""Analisis konten penelitian berikut dan ekstrak 5 topik utama penelitian.
Kembalikan HANYA dalam bentuk daftar bernomor, satu topik per baris. Gunakan Bahasa Indonesia.

Konten: {sample_text[:3000]}

Topik:"""

        topics_text = glm.generate(topic_prompt, max_tokens=200)
        topics = [
            line.strip()
            for line in topics_text.strip().split("\n")
            if line.strip() and line.strip()[0].isdigit()
        ]

        # ── Steps 2b/2c/2d run CONCURRENTLY (they are independent) ──────────
        # 2b: classify papers by basis · 2c: shared keywords/themes ·
        # 2d: per-paper weaknesses. Each is defined as a closure and executed in
        # parallel threads; the ollama client releases the GIL during requests.
        _set_analysis_job(job_id, message="Menganalisis basis, persamaan & kekurangan jurnal...")

        def _compute_groups():
            paper_list = "\n".join(
                f"- {p['title']}: {p['content'][:300]}" for p in paper_contents
            )
            group_prompt = (
                "Klasifikasikan setiap jurnal berikut berdasarkan BASIS utamanya "
                "(metode, algoritma, model, atau pendekatan inti yang digunakan). "
                "Gunakan label basis yang singkat dan konsisten dalam Bahasa Indonesia "
                "(mis. 'Algoritma Greedy', 'Deep Learning / CNN', 'Optimasi Metaheuristik'). "
                "Jurnal dengan basis serupa harus memakai label yang sama persis.\n\n"
                f"Daftar jurnal:\n{paper_list}\n\n"
                "Kembalikan HANYA JSON array (tanpa teks lain): "
                '[{"title": "judul jurnal", "basis": "label basis"}]'
            )
            raw_groups = glm.generate(group_prompt, max_tokens=400).strip()
            return _parse_paper_groups_json(raw_groups)

        def _compute_similarity():
            sim_block = "\n\n".join(
                f"Paper {i + 1}:\nJudul: {p['title']}\nKonten: {p['content'][:400]}"
                for i, p in enumerate(paper_contents)
            )
            sim_prompt = (
                "Analisis jurnal-jurnal berikut dan temukan PERSAMAANNYA. Gunakan Bahasa Indonesia.\n\n"
                f"{sim_block}\n\n"
                "Tugas:\n"
                "1. common_keywords: 5-8 kata kunci/konsep/metode yang SAMA atau berulang di jurnal-jurnal ini.\n"
                "2. shared_themes: 2-4 tema bersama (apa yang sama-sama dikerjakan jurnal-jurnal ini).\n"
                "3. summary: ringkasan 1-2 kalimat tentang benang merah jurnal-jurnal ini.\n\n"
                "Kembalikan HANYA JSON (tanpa teks lain): "
                '{"common_keywords": [...], "shared_themes": [...], "summary": "..."}'
            )
            raw_sim = glm.generate(sim_prompt, max_tokens=500, format="json")
            parsed_sim = _parse_selection_json(raw_sim if isinstance(raw_sim, str) else str(raw_sim))
            return {
                "common_keywords": parsed_sim.get("common_keywords", []),
                "shared_themes": parsed_sim.get("shared_themes", []),
                "summary": parsed_sim.get("summary", ""),
            }

        def _compute_weaknesses():
            def _weak_prompt(p):
                # Ground the analysis in the sections where authors actually
                # state weaknesses (Limitations / Future Work / Conclusion),
                # plus a short lead-in for context — NOT just the intro.
                weakness_ctx = (p.get("weakness_context") or "").strip()
                lead_in = (p.get("content") or "")[:600]
                evidence_block = (
                    f"[BAGIAN KETERBATASAN/KESIMPULAN JURNAL]\n{weakness_ctx}\n\n"
                    f"[CUPLIKAN AWAL JURNAL]\n{lead_in}"
                ) if weakness_ctx else f"Konten: {(p.get('content') or '')[:1800]}"
                return (
                    "Anda adalah reviewer jurnal ilmiah. Analisis SATU jurnal berikut dan temukan "
                    "KEKURANGAN/keterbatasannya secara KONKRET berdasarkan isinya (bukan tebakan umum).\n\n"
                    "Bedakan dua jenis. Untuk SETIAP poin WAJIB sertakan 'dasar' (bukti/alasan dari isi jurnal):\n"
                    "- tersurat: kelemahan yang DITULIS EKSPLISIT oleh penulis. WAJIB sertakan 'kutipan' = "
                    "potongan kalimat (5-20 kata) yang DISALIN PERSIS dari teks jurnal (verbatim) tempat "
                    "kelemahan itu disebut (mis. bagian keterbatasan, saran, atau future work). 'dasar' = "
                    "parafrase singkat dari kutipan itu.\n"
                    "- tersirat: kelemahan yang TIDAK ditulis tapi DISIMPULKAN dari isi. 'dasar' = fakta "
                    "spesifik di jurnal yang jadi alasannya (mis. 'hanya menguji 1 dataset', 'tidak ada "
                    "perbandingan dengan metode lain', 'tidak ada uji statistik', 'ruang lingkup hanya 1 kasus').\n\n"
                    "LARANGAN: jangan memakai kata ragu seperti 'mungkin', 'sepertinya', 'kemungkinan', "
                    "'bisa jadi'. Nyatakan observasi + simpulan secara tegas. Jika tidak ada dasar nyata di "
                    "teks, JANGAN mengarang poin (kembalikan array kosong saja). Untuk tersurat, kalau tidak "
                    "ada kutipan verbatim yang bisa disalin, JANGAN buat poin tersurat.\n\n"
                    f"Judul: {p['title']}\n"
                    f"{evidence_block}\n\n"
                    "Aturan: maksimal 3 poin per kategori; 'poin' = 1 kalimat singkat & spesifik, "
                    "'dasar' = 1 kalimat berisi bukti dari jurnal. Gunakan Bahasa Indonesia.\n"
                    "Kembalikan HANYA JSON (tanpa teks lain): "
                    '{"tersurat": [{"poin": "...", "dasar": "...", "kutipan": "..."}], '
                    '"tersirat": [{"poin": "...", "dasar": "..."}]}'
                )

            prompts = [_weak_prompt(p) for p in paper_contents]
            raws = glm.generate_batch(prompts, max_tokens=600, format="json")
            out = []
            for p, raw_weak in zip(paper_contents, raws):
                parsed_weak = _parse_weaknesses_json(
                    raw_weak if isinstance(raw_weak, str) else str(raw_weak)
                )
                # Verify each point against the paper text so the UI's promise
                # ("disertai dasar dari jurnal — bukan tebakan") actually holds.
                verified = _verify_paper_weaknesses(
                    parsed_weak, p.get("full_content", ""),
                    source_name=p.get("source", ""),
                    vector_store=vector_store,
                    analysis_job_id=job_id,
                )
                out.append({
                    "title": p["title"],
                    "source": p["source"],
                    "tersurat": verified["tersurat"],
                    "tersirat": verified["tersirat"],
                })
            return out

        paper_groups = []
        paper_similarity = {"common_keywords": [], "shared_themes": [], "summary": ""}
        paper_weaknesses = []

        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as _stage_pool:
            _f_groups = _stage_pool.submit(_compute_groups)
            _f_sim = _stage_pool.submit(_compute_similarity)
            _f_weak = _stage_pool.submit(_compute_weaknesses)
            try:
                paper_groups = _f_groups.result()
            except Exception as group_err:
                logger.warning(f"Paper grouping failed: {group_err}")
            try:
                paper_similarity = _f_sim.result()
            except Exception as sim_err:
                logger.warning(f"Paper similarity analysis failed: {sim_err}")
            try:
                paper_weaknesses = _f_weak.result()
            except Exception as weak_err:
                logger.warning(f"Paper weakness analysis failed: {weak_err}")

        _ensure_job_active(job_id)

        # ── Step 3: Run Coordinator (full neuro-symbolic pipeline) ──
        _set_analysis_job(
            job_id,
            progress=30,
            message="Running neuro-symbolic analysis (Observe \u2192 Think \u2192 Act \u2192 Evaluate)...",
        )

        coordinator_result = None
        execution_mode = "llm_fallback"
        reasoning_trace = []
        gap_indicators = []
        rule_engine_report = {}
        fact_table_stats = {}

        try:
            coordinator = analysis_context.coordinator
            main_topic = topics[0] if topics else "research analysis"

            coordinator_result = coordinator.process_research_query(
                query=main_topic,
                context={
                    "topics": topics,
                    "paper_contents": paper_contents,
                    "total_chunks": total_chunks,
                },
            )

            execution_mode = coordinator_result.get("execution_mode", "sequential")
            reasoning_trace = coordinator_result.get("reasoning_trace", [])
            gap_indicators = coordinator_result.get("gap_indicators", [])
            rule_engine_report = coordinator_result.get("rule_engine_report", {})
            fact_table_stats = coordinator_result.get("fact_table_stats", {})

            _set_analysis_job(
                job_id,
                progress=70,
                message=f"Coordinator complete ({execution_mode}). Generating summary...",
            )

            _ensure_job_active(job_id)
            record_job_event(job_id, "phase.started", phase="neuro_symbolic", status="running")

            logger.info(
                f"Coordinator finished: mode={execution_mode}, "
                f"gaps={len(gap_indicators)}, "
                f"facts={fact_table_stats.get('total_facts', 0)}"
            )
            record_job_event(
                job_id,
                "phase.completed",
                phase="neuro_symbolic",
                status="running",
                data={
                    "indicators": len(gap_indicators),
                    "facts": fact_table_stats.get("total_facts", 0),
                },
            )

        except Exception as e:
            logger.warning(f"Coordinator pipeline failed, falling back to LLM: {e}")
            _set_analysis_job(job_id, message="Coordinator unavailable, using LLM fallback...")
            reasoning_trace.append({
                "phase": "coordinator_fallback",
                "error": str(e),
            })

        # ── Step 4: Generate summary (always via LLM) ──────────
        _set_analysis_job(job_id, progress=75, message="Generating research summary...")
        _ensure_job_active(job_id)

        if topics:
            search_results = analysis_context.retriever.retrieve(topics[0], top_k=15)
            context = "\n\n".join(
                [f"Document {i+1}: {r.document.content}" for i, r in enumerate(search_results)]
            )

            summary_prompt = f"""Berikan ringkasan penelitian yang komprehensif untuk topik: {topics[0]}
Gunakan Bahasa Indonesia.

Konteks dari paper:
{context[:3000]}

Ringkasan:"""
            summary = glm.generate(summary_prompt, max_tokens=500)
        else:
            summary = "No topics extracted."

        # ── Step 5: Gap detection (use coordinator result or LLM fallback) ──
        _set_analysis_job(job_id, progress=80, message="Finalizing gap analysis...")
        _ensure_job_active(job_id)

        gaps = []
        if gap_indicators:
            # Coordinator returned structured gap indicators — normalise to dicts
            for gi in gap_indicators:
                gaps.append({
                    "title": gi.get("title", ""),
                    "description": gi.get("description", ""),
                    "type": gi.get("type", gi.get("indicator_type", "FRAGMENTATION")),
                    "confidence": gi.get("confidence", 0.0),
                    "rule_engine_verdict": gi.get("rule_engine_verdict", None),
                    "evidence": gi.get("evidence", []),
                    "suggested_directions": gi.get("suggested_directions", []),
                })
        else:
            # LLM fallback — generate structured gaps then validate via Rule Engine
            rule_engine = analysis_context.rule_engine

            for topic in topics[:3]:
                _ensure_job_active(job_id)
                search_results = analysis_context.retriever.retrieve(topic, top_k=10)
                context = "\n\n".join(
                    [f"Document {i+1}: {r.document.content}" for i, r in enumerate(search_results)]
                )

                gap_prompt = f"""Identifikasi SATU indikator SYNTHESIS GAP untuk topik: {topic}. Gunakan Bahasa Indonesia.

Definisi (Cooper, 1998; Booth et al., 2012) — synthesis gap HANYA salah satu dari 3 ini:
- FRAGMENTATION: paper membahas fenomena sama dari sudut berbeda tetapi tidak terintegrasi.
- INCONSISTENCY: temuan empiris antar-paper saling bertentangan dan belum direkonsiliasi.
- INCOMPLETENESS: aspek kritis fenomena belum dicakup bersama oleh paper-paper yang ada.

BUKAN synthesis gap (JANGAN keluarkan ini):
- kombinasi "Metode A + Domain B" yang belum ada (itu sekadar penerapan/belum diterapkan).
- topik yang sama sekali belum diteliti (itu knowledge gap).
- saran "future work" yang ditulis penulis paper (itu explicit gap).

Konteks dari paper:
{context[:2000]}

Kembalikan gap dalam format JSON TEPAT ini (tanpa teks tambahan):
{{"title": "Judul gap singkat", "description": "2-3 kalimat menjelaskan indikator gap berbasis perbandingan antar-paper", "type": "FRAGMENTATION atau INCONSISTENCY atau INCOMPLETENESS"}}

JSON:"""
                raw = glm.generate(gap_prompt, max_tokens=300).strip()

                # Parse LLM output into structured dict
                gap_dict = _parse_gap_json(raw)

                # Apply Rule Engine validation to LLM-generated gap
                verdict = None
                if rule_engine and gap_dict:
                    try:
                        claim = {
                            "claim": gap_dict.get("description", ""),
                            "indicator_type": gap_dict.get("type", "FRAGMENTATION"),
                        }
                        validation = rule_engine.validate(claim, {"topic": topic})
                        verdict = getattr(validation, "overall_verdict", None)
                        if isinstance(verdict, str):
                            pass
                        elif hasattr(verdict, "value"):
                            verdict = verdict.value
                        else:
                            verdict = str(verdict) if verdict else None

                        # Track in report
                        if verdict == "PASS":
                            rule_engine_report["passed"] = rule_engine_report.get("passed", 0) + 1
                        elif verdict == "FLAG":
                            rule_engine_report["flagged"] = rule_engine_report.get("flagged", 0) + 1
                        elif verdict == "REJECT":
                            rule_engine_report["rejected"] = rule_engine_report.get("rejected", 0) + 1
                        rule_engine_report["total"] = rule_engine_report.get("total", 0) + 1
                    except Exception as re_err:
                        logger.warning(f"Rule Engine validation failed for LLM gap: {re_err}")

                gap_dict["rule_engine_verdict"] = verdict
                gap_dict["confidence"] = gap_dict.get("confidence", 0.5)
                gap_dict["evidence"] = gap_dict.get("evidence", [])
                gap_dict["suggested_directions"] = gap_dict.get("suggested_directions", [])

                # Skip REJECT gaps
                if verdict != "REJECT":
                    gaps.append(gap_dict)

        # ── Step 6: Usulan penelitian (SELALU berlabuh ke indikator synthesis gap) ──
        # Sesuai revisi penguji: usulan harus mengacu pada 3 indikator Cooper/Booth
        # (fragmentasi, inkonsistensi, ketidaklengkapan kolektif), BUKAN kombinasi
        # metode+domain dangkal atau pengulangan "future work". Diposisikan sebagai
        # INDIKATOR usulan (decision-support) yang tetap perlu validasi peneliti.
        _set_analysis_job(
            job_id,
            progress=85,
            message="Menyusun usulan penelitian (berbasis indikator synthesis gap)...",
        )

        # Rekomendasi paper relevan dari coordinator disimpan terpisah sebagai rujukan,
        # bukan sebagai "usulan penelitian baru".
        related_paper_refs = []
        if coordinator_result and isinstance(coordinator_result.get("recommendations"), list):
            for r in coordinator_result["recommendations"]:
                if isinstance(r, dict) and r.get("title"):
                    related_paper_refs.append({
                        "title": r.get("title", ""),
                        "reason": r.get("reason", r.get("description", "")),
                    })

        gaps_context = "\n".join([
            f"- [{g.get('type','UNKNOWN')}] {g.get('title','')}: {g.get('description','')}"
            for i, g in enumerate(gaps)
        ]) or "(indikator gap belum terdeteksi secara eksplisit)"

        rec_prompt = f"""Anda membantu menyusun USULAN PENELITIAN BARU dari hasil sintesis beberapa jurnal.
Gunakan Bahasa Indonesia.

PENTING — kerangka synthesis gap (Cooper, 1998; Booth et al., 2012). Setiap usulan WAJIB
menjawab salah satu dari 3 indikator berikut:
1. FRAGMENTASI — jurnal membahas fenomena sama dari sudut berbeda tetapi tidak terintegrasi.
2. INKONSISTENSI — temuan antar-jurnal saling bertentangan dan belum direkonsiliasi.
3. KETIDAKLENGKAPAN KOLEKTIF — aspek kritis fenomena belum tercakup bersama oleh jurnal-jurnal itu.

LARANGAN KERAS (usulan seperti ini DITOLAK penguji):
- JANGAN mengusulkan sekadar "kombinasi Metode A + Domain B" (itu penerapan, bukan sintesis).
- JANGAN mengulang kalimat "future work"/saran yang sudah ditulis penulis jurnal (itu explicit gap).
- JANGAN mengusulkan topik yang sama sekali belum diteliti (itu knowledge gap, bukan synthesis gap).

Topik dari jurnal: {', '.join(topics[:3])}

Indikator synthesis gap yang terdeteksi:
{gaps_context}

Buat 5 usulan. Untuk tiap usulan:
- "title": judul usulan penelitian yang spesifik.
- "description": apa yang diteliti, dirumuskan sebagai upaya MENGINTEGRASIKAN / MEREKONSILIASI /
  MELENGKAPI literatur (sesuai indikator gap-nya).
- "gap_type": salah satu dari FRAGMENTATION / INCONSISTENCY / INCOMPLETENESS.
- "why": mengapa penting — sebutkan indikator gap mana yang dijawab.
- "how": metodologi yang disarankan secara ringkas.

Catatan: usulan ini bersifat INDIKATIF (alat bantu keputusan) dan tetap memerlukan
penilaian peneliti — jangan menyatakannya sebagai temuan yang pasti.

Kembalikan HANYA JSON array (tanpa teks tambahan):
[{{"title": "...", "description": "...", "gap_type": "FRAGMENTATION", "why": "...", "how": "..."}}]

JSON:"""
        try:
            raw = glm.generate(rec_prompt, max_tokens=800, format="json").strip()
            recommendations = _parse_recommendations_json(raw)
        except Exception as rec_err:
            logger.warning(f"Recommendation generation failed: {rec_err}")
            recommendations = []

        # Drop any leftover degenerate entries (e.g. "[INCOMPLETENESS]").
        recommendations = [
            r for r in recommendations
            if not (_is_degenerate_text(r.get("title", "")) and _is_degenerate_text(r.get("description", "")))
        ]

        # Robust fallback: if the (small) model produced nothing usable, synthesise
        # gap-anchored proposals deterministically from the detected gap indicators.
        if not recommendations and gaps:
            logger.info("LLM recommendations empty/degenerate — building deterministically from gaps.")
            recommendations = _build_recommendations_from_gaps(gaps)

        # ── Step 7: Roadmap (always via LLM) ────────────────────
        _set_analysis_job(job_id, progress=95, message="Creating roadmap...")
        _ensure_job_active(job_id)

        roadmap_topic = topics[0] if topics else "research"
        roadmap_prompt = f"""Buat peta jalan penelitian terstruktur untuk: {roadmap_topic}
Gunakan Bahasa Indonesia.

Kembalikan sebagai JSON array fase (tanpa teks tambahan):
[
  {{"phase": "Jangka Pendek (1-3 bulan)", "items": ["tugas 1", "tugas 2"]}},
  {{"phase": "Jangka Menengah (3-6 bulan)", "items": ["tugas 1", "tugas 2"]}},
  {{"phase": "Jangka Panjang (6-12 bulan)", "items": ["tugas 1", "tugas 2"]}}
]

JSON:"""
        raw_roadmap = glm.generate(roadmap_prompt, max_tokens=500, format="json").strip()
        roadmap = _parse_roadmap_json(raw_roadmap)

        # ── Step 8: Proposal intro (1-sentence AI synthesis, decision-support) ──
        proposal_intro = ""
        try:
            if recommendations:
                top_gap_desc = gaps[0].get("description", "") if gaps else ""
                top_gap_type = gaps[0].get("type", "") if gaps else ""
                top_rec = recommendations[0]
                rec_title = top_rec.get("title", "") if isinstance(top_rec, dict) else str(top_rec)
                intro_prompt = (
                    f"Tulis SATU kalimat ringkas (maksimal 40 kata) dalam Bahasa Indonesia yang "
                    f"merangkum INDIKATOR usulan penelitian hasil sintesis dari {len(paper_contents)} jurnal. "
                    f"Indikator synthesis gap ({top_gap_type}): {top_gap_desc}. Arah usulan: {rec_title}. "
                    f"Posisikan sebagai indikator/peluang yang masih PERLU DIVALIDASI peneliti — "
                    f"gunakan kata seperti 'berpotensi', 'mengindikasikan', atau 'dapat dipertimbangkan', "
                    f"JANGAN menyatakannya sebagai temuan pasti. Tanpa awalan 'Berikut' atau label."
                )
                proposal_intro = glm.generate(intro_prompt, max_tokens=120).strip()
        except Exception as intro_err:
            logger.warning(f"Proposal intro generation failed: {intro_err}")

        # ── Assemble final results ──────────────────────────────
        if not fact_table_stats:
            fact_table_stats = analysis_context.fact_table.get_statistics()

        # ── Compute evaluation metrics ────────────────────────
        eval_metrics = {}
        try:
            n_gaps = len(gaps)
            n_recs = len(recommendations)
            n_topics = len(topics)
            n_facts = fact_table_stats.get("total_facts", 0) if fact_table_stats else 0
            n_entities = fact_table_stats.get("total_entities", 0) if fact_table_stats else 0

            # Coverage: how many topics have at least one gap
            topic_coverage = min(n_gaps / max(n_topics, 1), 1.0)
            # Recommendation completeness: gaps addressed by recommendations
            rec_completeness = min(n_recs / max(n_gaps, 1), 1.0)
            # KG density: facts per entity
            kg_density = n_facts / max(n_entities, 1)
            # Pipeline completeness score
            pipeline_score = sum([
                0.2 if execution_mode == "langgraph" else 0.1,
                0.2 if n_facts > 0 else 0,
                0.2 if gap_indicators else 0,
                0.2 if rule_engine_report else 0,
                0.2 if n_recs > 0 else 0,
            ])

            eval_metrics = {
                "topic_coverage": round(topic_coverage, 3),
                "recommendation_completeness": round(rec_completeness, 3),
                "kg_density": round(kg_density, 3),
                "pipeline_score": round(pipeline_score, 3),
                "total_topics": n_topics,
                "total_gaps": n_gaps,
                "total_recommendations": n_recs,
                "total_facts": n_facts,
                "total_entities": n_entities,
            }
        except Exception as eval_err:
            logger.warning(f"Evaluation metrics computation failed: {eval_err}")

        _ensure_job_active(job_id)
        graph_snapshot = analysis_context.graph_snapshot()
        _set_analysis_job(
            job_id,
            status="completed",
            progress=100,
            message="Analysis complete!",
            results={
                "topics": topics,
                "summary": summary,
                "gaps": gaps,
                "recommendations": recommendations,
                "roadmap": roadmap,
                "total_chunks": total_chunks,
                "files_processed": len(pdf_paths),
                "papers": [p["title"] for p in paper_contents],
                "papers_info": [
                    {
                        "title": p["title"],
                        "source": p["source"],
                        "year": p.get("year"),
                        "similarity_percent": p.get("similarity_percent"),
                        "already_indexed": p["already_indexed"],
                    }
                    for p in paper_contents
                ],
                "new_papers": new_papers,
                "duplicate_papers": duplicate_papers,
                "paper_groups": paper_groups,
                "paper_similarity": paper_similarity,
                "paper_weaknesses": paper_weaknesses,
                "proposal_intro": proposal_intro,
                "related_paper_refs": related_paper_refs,
                "execution_mode": execution_mode,
                "gap_indicators": gap_indicators,
                "rule_engine_report": rule_engine_report,
                "fact_table_stats": fact_table_stats,
                "reasoning_trace": reasoning_trace,
                "eval_metrics": eval_metrics,
            },
            graph_snapshot=graph_snapshot,
        )
        record_job_event(
            job_id,
            "job.completed",
            status="completed",
            data={
                "files_processed": len(pdf_paths),
                "chunks": total_chunks,
                "indicators": len(gaps),
                "facts": fact_table_stats.get("total_facts", 0),
            },
        )

    except JobCancelled:
        _set_analysis_job(
            job_id,
            status="cancelled",
            message="Analisis dibatalkan oleh pengguna",
            error=None,
        )
        record_job_event(job_id, "job.cancelled", status="cancelled")
    except Exception as e:
        logger.error(f"Auto-analysis failed for job {job_id}: {e}")
        _set_analysis_job(
            job_id,
            status="failed",
            error="Analisis gagal. Silakan coba ulang atau periksa log server.",
            message="Analisis gagal. Silakan coba ulang.",
        )
        record_job_event(job_id, "job.failed", status="failed", data={"error_type": type(e).__name__})
    finally:
        # Inputs stay on disk until retention cleanup so a retry can rebuild a
        # clean scoped corpus after a restart.
        release_analysis_context(job_id)


# ───────────────────────────────────────────
# Knowledge Graph Visualization Endpoint
# ───────────────────────────────────────────

@router.get("/kg/graph")
async def get_kg_graph(job_id: str = None):
    """Return a persisted graph snapshot for one completed analysis job."""
    if not job_id:
        latest = get_latest_completed_job()
        job_id = latest.get("job_id") if latest else None
    data = get_job_graph(job_id) if job_id else None
    if not data:
        raise HTTPException(status_code=404, detail="No completed analysis graph found")
    raw_graph = data.get("raw_graph", {})
    return {
        "job_id": job_id,
        "nodes": raw_graph.get("nodes", []),
        "edges": raw_graph.get("edges", []),
        "stats": {
            "total_nodes": len(raw_graph.get("nodes", [])),
            "total_edges": len(raw_graph.get("edges", [])),
            "total_facts": len(data.get("facts", [])),
        },
    }


# ───────────────────────────────────────────
# SSE Streaming Endpoint
# ───────────────────────────────────────────

@router.get("/stream/{job_id}")
async def stream_analysis(job_id: str):
    """Stream analysis progress via Server-Sent Events."""

    async def event_generator():
        previous_revision = -1
        last_event_id = 0
        while True:
            job = _get_analysis_job(job_id)
            if not job:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                return

            status = job.get("status", "unknown")
            revision = int(job.get("revision", 0))
            if revision != previous_revision:
                payload = {
                    "type": "progress",
                    "status": status,
                    "message": job.get("message", ""),
                    "progress": job.get("progress", 0),
                    "revision": revision,
                }
                if status == "completed":
                    payload["type"] = "complete"
                    payload["results"] = job.get("results")
                elif status in ("failed", "interrupted", "cancelled"):
                    payload["type"] = "error"
                    payload["error"] = job.get("error", "")
                yield f"data: {json.dumps(payload, default=str)}\n\n"
                previous_revision = revision

            for event in get_job_events(job_id, after_event_id=last_event_id):
                last_event_id = event["id"]
                yield f"data: {json.dumps({'type': 'phase', **event}, default=str)}\n\n"

            if status in ("completed", "failed", "interrupted", "cancelled"):
                return

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
