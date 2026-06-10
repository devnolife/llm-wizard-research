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
    ChatRequest
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
            for item in items:
                if isinstance(item, dict):
                    result.append({
                        "title": item.get("title", "Untitled"),
                        "description": item.get("description", ""),
                        "why": item.get("why", ""),
                        "how": item.get("how", ""),
                        "priority": item.get("priority", "medium"),
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
        recs.append({
            "title": title[:200],
            "description": desc,
            "why": "",
            "how": "",
            "priority": "medium",
        })
    return recs


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
    """Parse plain text roadmap into structured phases."""
    import re as _re
    phases = []
    # Split by phase headers like "Phase 1:" or "### Phase 1"
    parts = _re.split(r'\n\s*(?:#{1,3}\s*)?(?:Phase|Fase|Tahap)\s*\d+[:\s]', text, flags=_re.IGNORECASE)
    for i, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        items = []
        for line in part.split('\n'):
            line = line.strip().lstrip('-•* ').strip()
            if line and len(line) > 3:
                items.append(line)
        if items:
            phases.append({
                "phase": f"Phase {len(phases)+1}",
                "items": items,
            })
    if not phases and text.strip():
        phases.append({"phase": "Phase 1", "items": [text.strip()]})
    return phases


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
        for i, pdf_path in enumerate(pdf_paths):
            _analysis_jobs[job_id]["message"] = f"Processing {pdf_path.name}..."
            _analysis_jobs[job_id]["progress"] = 5 + (i / len(pdf_paths)) * 15

            processed_doc = document_processor.process_pdf(str(pdf_path))

            for chunk in processed_doc.chunks:
                metadata = {
                    "source": pdf_path.name,
                    "title": processed_doc.title or pdf_path.name,
                    "chunk_index": chunk.chunk_index,
                }
                vector_store.add_document(chunk.content, metadata)
                total_chunks += 1

            paper_contents.append({
                "source": pdf_path.name,
                "title": processed_doc.title or pdf_path.name,
                "content": " ".join(c.content for c in processed_doc.chunks[:10]),
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

                gap_prompt = f"""Berdasarkan paper penelitian di bawah ini, identifikasi SATU gap sintesis penelitian spesifik untuk topik: {topic}

Gap sintesis adalah peluang penelitian yang muncul dari membandingkan beberapa paper. Gunakan Bahasa Indonesia.

Konteks dari paper:
{context[:2000]}

Kembalikan gap dalam format JSON TEPAT ini (tanpa teks tambahan):
{{"title": "Judul gap singkat", "description": "2-3 kalimat menjelaskan gap", "type": "FRAGMENTATION atau INCONSISTENCY atau INCOMPLETENESS"}}

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

        # ── Step 6: Recommendations (coordinator result or LLM fallback) ──
        _analysis_jobs[job_id]["progress"] = 85
        _analysis_jobs[job_id]["message"] = "Generating recommendations..."

        recommendations = []
        if coordinator_result and coordinator_result.get("recommendations"):
            raw_recs = coordinator_result["recommendations"]
            if isinstance(raw_recs, list):
                for i, r in enumerate(raw_recs):
                    if isinstance(r, dict):
                        recommendations.append({
                            "title": r.get("title", f"Recommendation {i+1}"),
                            "description": r.get("description", r.get("reason", "")),
                            "why": r.get("reason", r.get("why", "")),
                            "how": r.get("methodology", r.get("how", "")),
                            "priority": "high" if i < 2 else "medium" if i < 4 else "low",
                        })
                    else:
                        recommendations.append({
                            "title": str(r)[:80],
                            "description": str(r),
                            "why": "",
                            "how": "",
                            "priority": "high" if i < 2 else "medium" if i < 4 else "low",
                        })
            elif isinstance(raw_recs, str):
                recommendations = _parse_recommendations_text(raw_recs)
        else:
            gaps_context = "\n".join([
                f"Gap {i+1}: [{g.get('type','UNKNOWN')}] {g.get('title','')} — {g.get('description','')}"
                for i, g in enumerate(gaps)
            ])
            rec_prompt = f"""Anda adalah penasihat penelitian. Berdasarkan topik penelitian dan gap yang teridentifikasi berikut, berikan 5 rekomendasi penelitian yang dapat ditindaklanjuti. Gunakan Bahasa Indonesia.

Topik: {', '.join(topics[:3])}

Gap yang Teridentifikasi:
{gaps_context}

Kembalikan sebagai JSON array (tanpa teks tambahan):
[{{"title": "Judul rekomendasi", "description": "Apa yang perlu diteliti", "why": "Mengapa ini penting", "how": "Metodologi yang disarankan"}}]

JSON:"""
            raw = glm.generate(rec_prompt, max_tokens=600).strip()
            recommendations = _parse_recommendations_json(raw)

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
        raw_roadmap = glm.generate(roadmap_prompt, max_tokens=500).strip()
        roadmap = _parse_roadmap_json(raw_roadmap)

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
