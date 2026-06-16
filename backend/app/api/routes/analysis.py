"""
Analysis and recommendation endpoints

Updated to support:
- Gap indicators (Fragmentation / Inconsistency / Incompleteness)
- Rule Engine validation verdicts
- Fact Table statistics
- Agent reasoning trace
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse
from loguru import logger
from typing import List
from pathlib import Path
import asyncio
import tempfile
import uuid
import time
import json

from ...models.requests import (
    RecommendationRequest,
    GapDetectionRequest,
    ChatRequest,
    MarkedPapersRequest
)
from ...models.responses import (
    AnalysisResponseModel,
    GapIndicatorModel,
    RuleEngineReportModel,
    FactTableStatsModel,
)
from ..dependencies import (
    get_coordinator,
    get_gap_analyzer,
    get_retriever,
    get_glm_interface,
    get_vector_store,
    get_document_processor,
    get_fact_table,
    get_fact_extractor,
    get_rule_engine,
    get_knowledge_graph,
)
from ...utils.document_processor import DocumentProcessor

router = APIRouter()

# Job storage for async analysis
_analysis_jobs = {}


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
        coordinator = get_coordinator()
        
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
        gap_analyzer = get_gap_analyzer()
        retriever = get_retriever()
        
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
            rule_engine = get_rule_engine()
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
            fact_table = get_fact_table()
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
    """Chat with the research assistant (sync → threadpool)"""
    try:
        glm = get_glm_interface()
        
        conversation_id = getattr(request, "conversation_id", None) or str(uuid.uuid4())
        
        response = glm.chat(
            message=request.message,
            use_history=request.use_history
        )
        
        # Attempt to find relevant sources
        sources = []
        try:
            retriever = get_retriever()
            results = retriever.retrieve(query=request.message, top_k=3)
            sources = [
                r.document.metadata.get("title", r.document.metadata.get("source", ""))
                for r in results if r.document.metadata
            ]
        except Exception:
            pass
        
        return {
            "message": request.message,
            "response": response,
            "conversation_id": conversation_id,
            "sources": sources,
        }
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _parse_selection_json(raw: str) -> dict:
    """Parse LLM JSON output for the marked-papers analysis."""
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
                    sugg.append({
                        "title": s.get("title", s.get("judul", "")),
                        "rationale": s.get("rationale", s.get("alasan", "")),
                    })
                elif isinstance(s, str):
                    sugg.append({"title": s, "rationale": ""})
            return {
                "common_keywords": [str(k) for k in data.get("common_keywords", data.get("kata_kunci", []))],
                "shared_themes": [str(t) for t in data.get("shared_themes", data.get("tema", []))],
                "suggestions": sugg,
                "summary": data.get("summary", data.get("ringkasan", "")),
            }
    except (_json.JSONDecodeError, ValueError):
        pass
    return {"common_keywords": [], "shared_themes": [], "suggestions": [], "summary": text[:500]}


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
        """Normalise weakness items to {poin, dasar} objects (handles legacy strings)."""
        out = []
        for it in items if isinstance(items, list) else []:
            if isinstance(it, dict):
                poin = str(
                    it.get("poin", it.get("point", it.get("kelemahan", it.get("kekurangan", ""))))
                ).strip().lstrip('-•* ').strip()
                dasar = str(
                    it.get("dasar", it.get("basis", it.get("alasan", it.get("bukti", ""))))
                ).strip()
                if poin:
                    out.append({"poin": poin, "dasar": dasar})
            else:
                s = str(it).strip().lstrip('-•* ').strip()
                if s:
                    out.append({"poin": s, "dasar": ""})
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
            f"Abstrak: {str(p.get('abstract', '') or '')[:500]}"
            for i, p in enumerate(papers)
        ])

        topic_line = f"Topik/kata kunci pencarian awal: {request.query}\n\n" if request.query else ""

        prompt = (
            "Anda adalah asisten peneliti. Pengguna telah menandai beberapa paper secara manual. "
            "Analisis paper-paper berikut dan temukan benang merahnya. Gunakan Bahasa Indonesia.\n\n"
            f"{topic_line}{paper_block}\n\n"
            "Tugas:\n"
            "1. common_keywords: daftar 5-8 kata kunci/konsep/metode yang SAMA atau berulang di paper-paper tersebut.\n"
            "2. shared_themes: 2-4 tema bersama (apa yang sama-sama dikerjakan paper-paper ini).\n"
            "3. suggestions: 3-5 saran arah penelitian baru yang bisa dikembangkan dari gabungan paper ini, "
            "masing-masing dengan 'title' (judul singkat) dan 'rationale' (alasan singkat).\n"
            "4. summary: ringkasan 1-2 kalimat.\n\n"
            "Kembalikan HANYA JSON (tanpa teks lain) dengan struktur: "
            '{"common_keywords": [...], "shared_themes": [...], '
            '"suggestions": [{"title": "...", "rationale": "..."}], "summary": "..."}'
        )

        raw = glm.generate(prompt, max_tokens=800, format="json")
        result = _parse_selection_json(raw if isinstance(raw, str) else str(raw))
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
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    """
    Upload PDFs and automatically analyze them.
    Returns job_id to track progress.
    """
    try:
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Initialize job status
        _analysis_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting analysis...",
            "results": None,
            "error": None,
            "created_at": time.time()
        }
        
        # Save uploaded files temporarily
        temp_files = []
        for file in files:
            if not file.filename.endswith('.pdf'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not a PDF")
            
            temp_path = Path(tempfile.gettempdir()) / f"{uuid.uuid4()}_{file.filename}"
            with open(temp_path, 'wb') as f:
                content = await file.read()
                f.write(content)
            temp_files.append(temp_path)
        
        # Start background analysis
        background_tasks.add_task(process_auto_analysis, job_id, temp_files)
        
        return {
            "success": True,
            "job_id": job_id,
            "files_count": len(files),
            "message": "Analysis started. Use /api/analysis-status/{job_id} to check progress."
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analysis-status/{job_id}")
async def get_analysis_status(job_id: str, lang: str = "en"):
    """Get the status of an analysis job
    
    Args:
        job_id: The job ID
        lang: Language for results (en/id). Default: en
    """
    if job_id not in _analysis_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = _analysis_jobs[job_id]
    
    # Enrich completed results with rule_engine / fact_table info
    if job["status"] == "completed" and job.get("results"):
        results = job["results"]
        
        # Add rule_engine_report if not present
        if "rule_engine_report" not in results:
            results["rule_engine_report"] = {}
        
        # Add fact_table_stats if not present
        if "fact_table_stats" not in results:
            try:
                ft = get_fact_table()
                if ft:
                    results["fact_table_stats"] = ft.get_statistics()
            except Exception:
                results["fact_table_stats"] = {}
        
        # Add reasoning_trace placeholder
        if "reasoning_trace" not in results:
            results["reasoning_trace"] = []
    
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


def _parse_recommendations_json(raw: str) -> list:
    """Parse LLM JSON output for recommendations."""
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
            for idx, item in enumerate(items):
                if isinstance(item, dict):
                    title = _clean_rec_field(item.get("title", ""))
                    description = _clean_rec_field(item.get("description", ""))
                    # Skip degenerate items (e.g. title/desc that is just "[INCOMPLETENESS]")
                    if _is_degenerate_text(title) and _is_degenerate_text(description):
                        continue
                    # Priority by rank when the model doesn't supply one, so the
                    # frontend can pick a sensible primary proposal.
                    default_priority = "high" if idx < 2 else "medium" if idx < 4 else "low"
                    result.append({
                        "title": title or "Usulan penelitian",
                        "description": description,
                        "gap_type": str(item.get("gap_type", item.get("type", ""))).upper(),
                        "why": item.get("why", ""),
                        "how": item.get("how", ""),
                        "priority": item.get("priority", default_priority),
                    })
            return result
    except (_json.JSONDecodeError, ValueError):
        pass
    return _parse_recommendations_text(text)


def _parse_recommendations_text(text: str) -> list:
    """Parse plain text recommendations into structured dicts."""
    import re as _re
    recs = []
    items = _re.split(r'\n\s*(?:\d+[\.\)]\s*|-\s+)', text)
    for item in items:
        item = item.strip()
        if not item or len(item) < 10:
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


def process_auto_analysis(job_id: str, pdf_paths: List[Path]):
    """Background task to process PDFs and run full neuro-symbolic analysis.

    NOTE: deliberately a SYNC function — FastAPI runs sync background tasks
    in the threadpool, keeping the event loop free. Declaring it `async def`
    (without awaits) would run the whole multi-minute LLM pipeline ON the
    event loop and block every other request (upload timeouts).
    """
    try:
        _analysis_jobs[job_id]["progress"] = 5
        _analysis_jobs[job_id]["message"] = "Processing PDFs..."

        vector_store = get_vector_store()
        document_processor = DocumentProcessor()
        glm = get_glm_interface()

        # ── Step 0: Clear fact table and KG for fresh analysis ──
        # NOTE: We keep existing vector store documents and only add new ones.
        # Fact table and KG are per-analysis artifacts so they are cleared.
        try:
            ft = get_fact_table()
            if ft:
                ft.clear()
        except Exception:
            pass
        try:
            kg = get_knowledge_graph()
            if kg and hasattr(kg, 'graph'):
                kg.graph.clear()
        except Exception:
            pass

        # ── Step 1: Ingest PDFs into vector store ──────────────
        total_chunks = 0
        paper_contents = []
        new_papers = 0
        duplicate_papers = 0
        for i, pdf_path in enumerate(pdf_paths):
            # Temp files are named "{uuid}_{original}"; recover the original name
            # so duplicate detection & metadata use the real filename, not the UUID.
            source_name = pdf_path.name.split('_', 1)[-1]
            _analysis_jobs[job_id]["message"] = f"Processing {source_name}..."
            _analysis_jobs[job_id]["progress"] = 5 + (i / len(pdf_paths)) * 15

            processed_doc = document_processor.process_pdf(str(pdf_path))

            # Skip re-indexing if this file is already in the vector store
            already_indexed = vector_store.count_by_source(source_name) > 0
            if already_indexed:
                duplicate_papers += 1
                _analysis_jobs[job_id]["message"] = f"{source_name} sudah ada di database — melewati pengindeksan."
                logger.info(f"Skipping ingestion for already-indexed paper: {source_name}")
            else:
                for chunk in processed_doc.chunks:
                    metadata = {
                        "source": source_name,
                        "title": processed_doc.title or source_name,
                        "chunk_index": chunk.chunk_index,
                    }
                    vector_store.add_document(chunk.content, metadata)
                    total_chunks += 1
                new_papers += 1

            paper_contents.append({
                "source": source_name,
                "title": processed_doc.title or source_name,
                "content": " ".join(c.content for c in processed_doc.chunks[:10]),
                "already_indexed": already_indexed,
            })
            pdf_path.unlink()

        _analysis_jobs[job_id]["progress"] = 20
        _analysis_jobs[job_id]["message"] = "Extracting topics..."

        # ── Step 2: Extract topics from UPLOADED papers only ────
        uploaded_sources = [p["source"] for p in paper_contents]
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
        _analysis_jobs[job_id]["message"] = "Menganalisis basis, persamaan & kekurangan jurnal..."

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
                return (
                    "Anda adalah reviewer jurnal ilmiah. Analisis SATU jurnal berikut dan temukan "
                    "KEKURANGAN/keterbatasannya secara KONKRET berdasarkan isinya (bukan tebakan umum).\n\n"
                    "Bedakan dua jenis. Untuk SETIAP poin WAJIB sertakan 'dasar' (bukti/alasan dari isi jurnal):\n"
                    "- tersurat: kelemahan yang DITULIS EKSPLISIT oleh penulis. 'dasar' = parafrase/kutipan "
                    "bagian teks yang menyebutkannya (mis. bagian keterbatasan, saran, atau future work).\n"
                    "- tersirat: kelemahan yang TIDAK ditulis tapi DISIMPULKAN dari isi. 'dasar' = fakta "
                    "spesifik di jurnal yang jadi alasannya (mis. 'hanya menguji 1 dataset', 'tidak ada "
                    "perbandingan dengan metode lain', 'tidak ada uji statistik', 'ruang lingkup hanya 1 kasus').\n\n"
                    "LARANGAN: jangan memakai kata ragu seperti 'mungkin', 'sepertinya', 'kemungkinan', "
                    "'bisa jadi'. Nyatakan observasi + simpulan secara tegas. Jika tidak ada dasar nyata di "
                    "teks, JANGAN mengarang poin (kembalikan array kosong saja).\n\n"
                    f"Judul: {p['title']}\n"
                    f"Konten: {p['content'][:1800]}\n\n"
                    "Aturan: maksimal 3 poin per kategori; 'poin' = 1 kalimat singkat & spesifik, "
                    "'dasar' = 1 kalimat berisi bukti dari jurnal. Gunakan Bahasa Indonesia.\n"
                    "Kembalikan HANYA JSON (tanpa teks lain): "
                    '{"tersurat": [{"poin": "...", "dasar": "..."}], '
                    '"tersirat": [{"poin": "...", "dasar": "..."}]}'
                )

            prompts = [_weak_prompt(p) for p in paper_contents]
            raws = glm.generate_batch(prompts, max_tokens=600, format="json")
            out = []
            for p, raw_weak in zip(paper_contents, raws):
                parsed_weak = _parse_weaknesses_json(
                    raw_weak if isinstance(raw_weak, str) else str(raw_weak)
                )
                out.append({
                    "title": p["title"],
                    "source": p["source"],
                    "tersurat": parsed_weak["tersurat"],
                    "tersirat": parsed_weak["tersirat"],
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

        # ── Step 3: Run Coordinator (full neuro-symbolic pipeline) ──
        _analysis_jobs[job_id]["progress"] = 30
        _analysis_jobs[job_id]["message"] = "Running neuro-symbolic analysis (Observe \u2192 Think \u2192 Act \u2192 Evaluate)..."

        coordinator_result = None
        execution_mode = "llm_fallback"
        reasoning_trace = []
        gap_indicators = []
        rule_engine_report = {}
        fact_table_stats = {}

        try:
            coordinator = get_coordinator()
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

            _analysis_jobs[job_id]["progress"] = 70
            _analysis_jobs[job_id]["message"] = f"Coordinator complete ({execution_mode}). Generating summary..."

            logger.info(
                f"Coordinator finished: mode={execution_mode}, "
                f"gaps={len(gap_indicators)}, "
                f"facts={fact_table_stats.get('total_facts', 0)}"
            )

        except Exception as e:
            logger.warning(f"Coordinator pipeline failed, falling back to LLM: {e}")
            _analysis_jobs[job_id]["message"] = "Coordinator unavailable, using LLM fallback..."
            reasoning_trace.append({
                "phase": "coordinator_fallback",
                "error": str(e),
            })

        # ── Step 4: Generate summary (always via LLM) ──────────
        _analysis_jobs[job_id]["progress"] = 75
        _analysis_jobs[job_id]["message"] = "Generating research summary..."

        if topics:
            source_filter = {"source": {"$in": uploaded_sources}} if len(uploaded_sources) > 1 else {"source": uploaded_sources[0]}
            search_results = vector_store.search(topics[0], top_k=15, filter_metadata=source_filter)
            if not search_results:
                search_results = vector_store.search(topics[0], top_k=15)
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
        _analysis_jobs[job_id]["progress"] = 80
        _analysis_jobs[job_id]["message"] = "Finalizing gap analysis..."

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
            rule_engine = None
            try:
                rule_engine = get_rule_engine()
            except Exception:
                pass

            for topic in topics[:3]:
                source_filter = {"source": {"$in": uploaded_sources}} if len(uploaded_sources) > 1 else {"source": uploaded_sources[0]}
                search_results = vector_store.search(topic, top_k=10, filter_metadata=source_filter)
                if not search_results:
                    search_results = vector_store.search(topic, top_k=10)
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
        _analysis_jobs[job_id]["progress"] = 85
        _analysis_jobs[job_id]["message"] = "Menyusun usulan penelitian (berbasis indikator synthesis gap)..."

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
        _analysis_jobs[job_id]["progress"] = 95
        _analysis_jobs[job_id]["message"] = "Creating roadmap..."

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
            try:
                ft = get_fact_table()
                if ft:
                    fact_table_stats = ft.get_statistics()
            except Exception:
                pass

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

        _analysis_jobs[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "Analysis complete!",
            "results": {
                "topics": topics,
                "summary": summary,
                "gaps": gaps,
                "recommendations": recommendations,
                "roadmap": roadmap,
                "total_chunks": total_chunks,
                "files_processed": len(pdf_paths),
                "papers": [p["title"] for p in paper_contents],
                "papers_info": [
                    {"title": p["title"], "source": p["source"], "already_indexed": p["already_indexed"]}
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
        })

    except Exception as e:
        logger.error(f"Auto-analysis failed for job {job_id}: {e}")
        _analysis_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "message": f"Analysis failed: {str(e)}",
        })


# ───────────────────────────────────────────
# Knowledge Graph Visualization Endpoint
# ───────────────────────────────────────────

@router.get("/kg/graph")
async def get_kg_graph(job_id: str = None):
    """Return KG nodes and edges for visualization.
    
    If job_id is provided, returns KG data from that analysis job's context.
    Otherwise returns current global KG state.
    """
    kg = get_knowledge_graph()
    data = kg.export_to_dict()
    return {
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "stats": {
            "total_nodes": len(data.get("nodes", [])),
            "total_edges": len(data.get("edges", [])),
        },
    }


# ───────────────────────────────────────────
# SSE Streaming Endpoint
# ───────────────────────────────────────────

@router.get("/stream/{job_id}")
async def stream_analysis(job_id: str):
    """Stream analysis progress via Server-Sent Events."""

    async def event_generator():
        prev_status = None
        prev_message = None
        while True:
            job = _analysis_jobs.get(job_id)
            if not job:
                yield f"data: {json.dumps({'type': 'error', 'message': 'Job not found'})}\n\n"
                return

            status = job.get("status", "unknown")
            message = job.get("message", "")

            if status != prev_status or message != prev_message:
                payload = {
                    "type": "progress",
                    "status": status,
                    "message": message,
                    "progress": job.get("progress", 0),
                }
                if status == "completed":
                    payload["type"] = "complete"
                    payload["results"] = job.get("results")
                elif status == "failed":
                    payload["type"] = "error"
                    payload["error"] = job.get("error", "")
                yield f"data: {json.dumps(payload, default=str)}\n\n"
                prev_status = status
                prev_message = message

            if status in ("completed", "failed"):
                return

            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
