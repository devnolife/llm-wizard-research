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
from datetime import datetime
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
    create_ephemeral_analysis_context,
    get_retriever,
    get_glm_interface,
    get_vector_store,
)
from ...utils.config_loader import get_config
from ...utils.job_store import (
    append_conversation_message,
    clear_conversation,
    get_conversation_messages,
    delete_job,
    get_job,
    get_job_events,
    get_job_graph,
    get_latest_completed_job,
    get_stage_artifacts,
    list_jobs,
    record_job_event,
    request_cancel,
    retry_job,
)
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload
from ...services.analysis_queue import get_analysis_queue
from ...services import skill_guidance
from ..auto_analysis import _get_analysis_job, _set_analysis_job
from .analysis_helpers import (
    _ground_selection_suggestions,
    _parse_selection_json,
)

router = APIRouter()

_CONVERSATION_LOCKS: dict[str, Lock] = {}
_CONVERSATION_LOCKS_GUARD = Lock()


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


@router.post("/analysis-jobs/{job_id}/reanalyze")
async def reanalyze_job(job_id: str):
    """Re-run any job as a NEW job from its retained input PDFs.

    Unlike ``retry`` (which requeues failed/cancelled jobs in place), this keeps
    the source job and its results intact — useful to re-run a completed
    analysis with the currently configured LLM engine and compare outcomes.
    """
    source = get_job(job_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan")
    source_paths = [Path(p) for p in (source.get("payload") or {}).get("pdf_paths") or []]
    if not source_paths or any(not p.exists() for p in source_paths):
        raise HTTPException(
            status_code=409,
            detail="PDF asli job ini sudah tidak tersedia; unggah ulang untuk menganalisis lagi",
        )

    config = get_config()
    new_job_id = str(uuid.uuid4())
    job_dir = Path(config.data.raw_path) / "analysis_jobs" / new_job_id
    job_dir.mkdir(parents=True, exist_ok=False)
    try:
        input_paths: list[Path] = []
        files_metadata = []
        for path in source_paths:
            target = job_dir / path.name
            shutil.copyfile(path, target)
            input_paths.append(target)
            # Inputs are stored as "{index}_{original-name}"; recover the name.
            files_metadata.append({"name": path.name.split("_", 1)[-1]})
    except Exception:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    # Keep the source job's pipeline so a research job is re-run as research,
    # not as the legacy 8-stage analysis; its outputs get a fresh directory.
    new_payload = {
        "pdf_paths": [str(path) for path in input_paths],
        "input_dir": str(job_dir),
        "files": files_metadata,
        "reanalyzed_from": job_id,
    }
    pipeline = source.get("pipeline")
    if pipeline:
        new_payload["output_dir"] = str(
            Path(config.data.processed_path) / pipeline / new_job_id
        )

    _set_analysis_job(
        new_job_id,
        status="queued",
        progress=0,
        message="Menunggu worker analisis...",
        results=None,
        error=None,
        created_at=time.time(),
        max_attempts=config.queue.max_attempts,
        pipeline=pipeline,
        payload=new_payload,
    )
    record_job_event(
        new_job_id,
        "job.created",
        status="queued",
        data={"file_count": len(input_paths), "reanalyzed_from": job_id},
    )
    get_analysis_queue().notify()
    return {
        "success": True,
        "job_id": new_job_id,
        "source_job_id": job_id,
        "files_count": len(input_paths),
        "message": "Analisis ulang diantrekan. Pantau /api/analysis-status/{job_id}.",
    }


def _conversation_lock(conversation_id: str) -> Lock:
    with _CONVERSATION_LOCKS_GUARD:
        return _CONVERSATION_LOCKS.setdefault(conversation_id, Lock())


# Translating a completed result is dozens of LLM calls; concurrent pollers of
# the same job must wait for the first translation instead of repeating it.
_TRANSLATION_LOCKS: dict[str, Lock] = {}
_TRANSLATION_LOCKS_GUARD = Lock()


def _translation_lock(job_id: str) -> Lock:
    with _TRANSLATION_LOCKS_GUARD:
        return _TRANSLATION_LOCKS.setdefault(job_id, Lock())


def _translate_results(glm, results: dict) -> dict:
    """Return an Indonesian copy of the user-facing fields of ``results``."""
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

    return {
        **results,
        "topics": translate_to_indonesian(glm, results.get("topics", [])),
        "summary": translate_to_indonesian(glm, results.get("summary", "")),
        "gaps": translated_gaps,
        "recommendations": translated_recs,
        "roadmap": translated_roadmap,
    }


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

        raw = glm.generate(
            skill_guidance.wrap_prompt("selection", prompt)[0],
            max_tokens=1000, format="json",
        )
        result = _parse_selection_json(raw if isinstance(raw, str) else str(raw))
        result["suggestions"] = _ground_selection_suggestions(result["suggestions"], papers)
        result["skills_used"] = skill_guidance.skills_for_phase("selection")
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
def get_analysis_status(job_id: str, lang: str = "en"):
    """Get the status of an analysis job.

    Args:
        job_id: The job ID
        lang: Language for results (en/id). Default: en

    Deliberately a plain ``def``: the ``lang=id`` path issues dozens of
    synchronous LLM calls, which would freeze the event loop (and every other
    request, including SSE streams) if this were a coroutine.
    """
    job = _get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    # Completed jobs already persist their isolated fact-table stats.  Never
    # consult the global singleton here: it can belong to another job.
    if job["status"] == "completed" and job.get("results"):
        results = dict(job["results"])
        result_changed = False
        for key, empty in (
            ("rule_engine_report", {}),
            ("fact_table_stats", {}),
            ("reasoning_trace", []),
        ):
            if key not in results:
                results[key] = empty
                result_changed = True
        if result_changed:
            # Persist only the changed field: ``job`` itself carries ``job_id``,
            # so splatting it into ``_set_analysis_job(job_id, **job)`` raises
            # ``TypeError: multiple values for argument 'job_id'``.
            job = _set_analysis_job(job_id, results=results)

    # Translate if requested and job is completed
    if lang == "id" and job["status"] == "completed" and job.get("results"):
        if not job.get("results_id"):
            with _translation_lock(job_id):
                job = _get_analysis_job(job_id) or job
                if not job.get("results_id"):
                    translated = _translate_results(get_glm_interface(), job["results"])
                    job = _set_analysis_job(job_id, results_id=translated)
        return {**job, "results": job["results_id"]}

    return job


@router.get("/analysis-status/{job_id}/events")
async def get_analysis_events(job_id: str, after_event_id: int = 0):
    """Riwayat event proses sebuah job (untuk timeline per-tahap).

    Mengembalikan seluruh event tersanitasi yang tercatat untuk job ini,
    terurut per ``event_id``. Dipakai UI proses untuk fetch awal (refresh-safe)
    dan meninjau ulang job yang sudah selesai/gagal.
    """
    job = _get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    events = get_job_events(job_id, after_event_id=after_event_id)
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "progress": job.get("progress"),
        "message": job.get("message"),
        "events": events,
    }


@router.get("/analysis-status/{job_id}/artifacts")
async def get_analysis_artifacts(job_id: str, phase: str | None = None):
    """Artefak hasil per tahap: hasil ekstraksi, output tiap tahap, dan
    prompt + jawaban mentah LLM (kind: ``extraction`` / ``result`` / ``llm``).

    Berbeda dari ``/events`` yang metadata-only, endpoint ini memuat konten
    (dengan cap ukuran) supaya UI proses bisa memperlihatkan hasil nyata.
    """
    job = _get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    artifacts = get_stage_artifacts(job_id, phase=phase)
    return {
        "job_id": job_id,
        "status": job.get("status"),
        "artifacts": artifacts,
    }


@router.get("/analysis-status/{job_id}/chunks")
async def get_analysis_chunks(job_id: str, format: str = "jsonl"):
    """Hasil tahap PDF→chunk untuk sebuah job, siap diunduh.

    Chunk lengkap tidak ikut disimpan di ``results`` (di sana hanya ada 3
    sampel per jurnal yang dipangkas 350 karakter), jadi teks utuhnya diambil
    kembali dari vector store berdasarkan daftar berkas milik job ini.

    ``format``:
      * ``jsonl`` — satu chunk per baris, untuk diproses program/agen.
      * ``md``    — dikelompokkan per jurnal, untuk dibaca manusia.
    """
    fmt = (format or "jsonl").lower()
    if fmt not in {"jsonl", "md"}:
        raise HTTPException(status_code=400, detail="format harus 'jsonl' atau 'md'")

    job = _get_analysis_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    results = job.get("results") or {}
    papers = results.get("papers_info") or []
    if not papers:
        raise HTTPException(
            status_code=409,
            detail="Job belum punya daftar jurnal — tunggu sampai analisis selesai.",
        )

    sources = [p.get("source") for p in papers if p.get("source")]
    titles = {p.get("source"): p.get("title") for p in papers}
    years = {p.get("source"): p.get("year") for p in papers}

    vector_store = get_vector_store()
    docs = vector_store.get_chunks_by_sources(sources)
    if not docs:
        raise HTTPException(
            status_code=410,
            detail=(
                "Chunk job ini sudah tidak ada di vector store (indeks mungkin "
                "telah dibersihkan). Jalankan ulang analisis untuk membuatnya lagi."
            ),
        )

    exported_at = datetime.now().isoformat(timespec="seconds")
    stem = f"chunks_{len(papers)}jurnal_{job_id[:8]}"

    if fmt == "jsonl":
        def _lines():
            meta = {
                "record": "meta",
                "job_id": job_id,
                "diekspor_pada": exported_at,
                "jumlah_jurnal": len(papers),
                "jumlah_chunk": len(docs),
                "jumlah_chunk_tercatat_job": results.get("total_chunks"),
                "catatan": (
                    "Baris berikutnya masing-masing satu chunk. Teks verbatim "
                    "hasil ekstraksi PDF, belum diringkas LLM."
                ),
            }
            yield json.dumps(meta, ensure_ascii=False) + "\n"
            for d in docs:
                m = d.metadata or {}
                src = m.get("source")
                authors = m.get("authors")
                if isinstance(authors, str):
                    authors = [a.strip() for a in authors.split(",") if a.strip()]
                yield json.dumps({
                    "record": "chunk",
                    "source": src,
                    "doi": m.get("doi"),
                    "paper_title": titles.get(src) or m.get("paper_title") or m.get("title"),
                    "authors": authors or [],
                    "year": years.get(src) or m.get("year"),
                    "language": m.get("language"),
                    "section_raw": m.get("section_raw") or m.get("section"),
                    "section_normalized": m.get("section_normalized"),
                    "is_reference": m.get("is_reference"),
                    "page_start": m.get("page_start"),
                    "chunk_index": m.get("chunk_index"),
                    "chunk_id": m.get("chunk_id"),
                    "token_count": m.get("token_count"),
                    "chars": len(d.content or ""),
                    "text": d.content,
                    "extraction_quality": m.get("extraction_quality"),
                }, ensure_ascii=False) + "\n"

        return StreamingResponse(
            _lines(),
            media_type="application/x-ndjson",
            headers={"Content-Disposition": f'attachment; filename="{stem}.jsonl"'},
        )

    def _md():
        total_chars = sum(len(d.content or "") for d in docs)
        yield (
            f"# Hasil ekstraksi PDF → chunk\n\n"
            f"- **Job:** `{job_id}`\n"
            f"- **Diekspor:** {exported_at}\n"
            f"- **Jurnal:** {len(papers)}\n"
            f"- **Chunk:** {len(docs)} (tercatat di job: "
            f"{results.get('total_chunks') or '—'})\n"
            f"- **Total karakter:** {total_chars:,}\n\n"
            "Teks di bawah ini verbatim hasil ekstraksi, belum diolah LLM. "
            "Chunk diurutkan per berkas lalu per `chunk_index`.\n"
        )
        current = None
        for d in docs:
            m = d.metadata or {}
            src = m.get("source")
            if src != current:
                current = src
                yield (
                    f"\n---\n\n## {titles.get(src) or src}\n\n"
                    f"- Berkas: `{src}`\n"
                    f"- Tahun: {years.get(src) or '—'}\n"
                )
            sec = m.get("section")
            head = f"\n### chunk {m.get('chunk_index')}"
            if sec:
                head += f" — {sec}"
            yield head + f" ({len(d.content or '')} karakter)\n\n{d.content}\n"

    return StreamingResponse(
        _md(),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{stem}.md"'},
    )


@router.get("/analysis-jobs")
async def list_analysis_jobs(limit: int = 20):
    """Daftar ringkas job analisis terbaru (untuk dashboard monitor)."""
    limit = max(1, min(int(limit), 100))
    jobs = []
    for job in list_jobs()[:limit]:
        results = job.get("results") or {}
        payload = job.get("payload") or {}
        pdf_paths = payload.get("pdf_paths") or []
        jobs.append({
            "job_id": job.get("job_id"),
            "status": job.get("status"),
            "progress": job.get("progress"),
            "message": job.get("message"),
            "pipeline": job.get("pipeline") or "legacy",
            "created_at": job.get("created_at"),
            "completed_at": job.get("completed_at"),
            "files": [Path(p).name for p in pdf_paths],
            "files_processed": results.get("files_processed"),
            "topics_count": len(results.get("topics") or []),
            "gaps_count": len(results.get("gaps") or []),
            "recommendations_count": len(results.get("recommendations") or []),
            "model": (results.get("llm_info") or {}).get("model"),
        })
    return {"jobs": jobs, "total": len(jobs)}


@router.delete("/analysis-jobs/{job_id}")
async def delete_analysis_job(job_id: str):
    """Hapus job beserta event, artefak, chunk vektor, dan file unggahannya."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") in ("queued", "running", "processing", "started"):
        raise HTTPException(
            status_code=409,
            detail="Job masih berjalan — batalkan dulu sebelum menghapus",
        )

    delete_job(job_id)

    # Best-effort cleanup of data outside the job store.
    try:
        get_vector_store().delete_by_metadata({"analysis_job_id": job_id})
    except Exception as exc:
        logger.warning(f"Could not delete vector chunks for job {job_id}: {exc}")
    try:
        job_dir = Path(get_config().data.raw_path) / "analysis_jobs" / job_id
        if job_dir.is_dir():
            shutil.rmtree(job_dir, ignore_errors=True)
    except Exception as exc:
        logger.warning(f"Could not delete upload dir for job {job_id}: {exc}")

    return {"deleted": True, "job_id": job_id}


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
