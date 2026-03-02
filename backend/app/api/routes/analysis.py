"""
Analysis and recommendation endpoints

Updated to support:
- Gap indicators (Fragmentation / Inconsistency / Incompleteness)
- Rule Engine validation verdicts
- Fact Table statistics
- Agent reasoning trace
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from loguru import logger
from typing import List
from pathlib import Path
import tempfile
import uuid
import time

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
    get_rule_engine,
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
async def recommend(request: RecommendationRequest):
    """Get research recommendations via the agentic pipeline"""
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
async def detect_gaps(request: GapDetectionRequest):
    """Detect synthesis gaps using the 3-indicator model"""
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
async def chat(request: ChatRequest):
    """Chat with the research assistant"""
    try:
        glm = get_glm_interface()
        
        response = glm.chat(
            message=request.message,
            use_history=request.use_history
        )
        
        return {
            "message": request.message,
            "response": response
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
            # Translate results to Indonesian
            glm = get_glm_interface()
            results = job["results"]
            
            job["results_id"] = {
                "topics": translate_to_indonesian(glm, results.get("topics", [])),
                "summary": translate_to_indonesian(glm, results.get("summary", "")),
                "gaps": translate_to_indonesian(glm, results.get("gaps", [])),
                "recommendations": translate_to_indonesian(glm, results.get("recommendations", "")),
                "roadmap": translate_to_indonesian(glm, results.get("roadmap", "")),
                "total_chunks": results.get("total_chunks"),
                "files_processed": results.get("files_processed")
            }
        
        # Return translated version
        return {
            **job,
            "results": job["results_id"]
        }
    
    return job


async def process_auto_analysis(job_id: str, pdf_paths: List[Path]):
    """Background task to process PDFs and run auto-analysis"""
    try:
        # Update status
        _analysis_jobs[job_id]["progress"] = 10
        _analysis_jobs[job_id]["message"] = "Processing PDFs..."
        
        # Get components
        vector_store = get_vector_store()
        document_processor = DocumentProcessor()
        glm = get_glm_interface()
        
        # Process each PDF
        total_chunks = 0
        for i, pdf_path in enumerate(pdf_paths):
            _analysis_jobs[job_id]["message"] = f"Processing {pdf_path.name}..."
            _analysis_jobs[job_id]["progress"] = 10 + (i / len(pdf_paths)) * 30
            
            # Process PDF
            processed_doc = document_processor.process_pdf(str(pdf_path))
            
            # Add to vector store
            for chunk in processed_doc.chunks:
                metadata = {
                    "source": pdf_path.name,
                    "title": processed_doc.title or pdf_path.name,
                    "chunk_index": chunk.chunk_index
                }
                vector_store.add_document(chunk.content, metadata)
                total_chunks += 1
            
            # Clean up temp file
            pdf_path.unlink()
        
        _analysis_jobs[job_id]["progress"] = 40
        _analysis_jobs[job_id]["message"] = "Extracting topics..."
        
        # Extract topics
        sample_docs = vector_store.collection.get(limit=50)
        sample_text = " ".join([doc for doc in sample_docs['documents'][:10]])
        
        topic_prompt = f"""Analyze this research content and extract 5 main research topics.
Return ONLY a numbered list, one topic per line.

Content: {sample_text[:2000]}

Topics:"""
        
        topics_text = glm.generate(topic_prompt, max_tokens=200)
        topics = [line.strip() for line in topics_text.strip().split('\n') if line.strip() and line.strip()[0].isdigit()]
        
        _analysis_jobs[job_id]["progress"] = 60
        _analysis_jobs[job_id]["message"] = "Generating research summary..."
        
        # Generate summary for main topic
        if topics:
            search_results = vector_store.search(topics[0], top_k=15)
            context = "\n\n".join([f"Document {i+1}: {r.document.content}" 
                                  for i, r in enumerate(search_results)])
            
            summary_prompt = f"""Provide a comprehensive research summary for: {topics[0]}

Context from papers:
{context[:3000]}

Summary:"""
            
            summary = glm.generate(summary_prompt, max_tokens=500)
        else:
            summary = "No topics extracted."
        
        _analysis_jobs[job_id]["progress"] = 75
        _analysis_jobs[job_id]["message"] = "Detecting research gaps..."
        
        # Detect gaps
        gaps = []
        for topic in topics[:3]:
            search_results = vector_store.search(topic, top_k=10)
            context = "\n\n".join([f"Document {i+1}: {r.document.content}" 
                                  for i, r in enumerate(search_results)])
            
            gap_prompt = f"""Identify ONE specific research gap for: {topic}

Context: {context[:2000]}

Research Gap:"""
            
            gap = glm.generate(gap_prompt, max_tokens=200)
            gaps.append(gap.strip())
        
        _analysis_jobs[job_id]["progress"] = 85
        _analysis_jobs[job_id]["message"] = "Generating recommendations..."
        
        # Generate recommendations
        rec_prompt = f"""Based on these topics: {', '.join(topics[:3])}

Provide 5 specific research recommendations:"""
        
        recommendations = glm.generate(rec_prompt, max_tokens=300)
        
        _analysis_jobs[job_id]["progress"] = 95
        _analysis_jobs[job_id]["message"] = "Creating roadmap..."
        
        # Generate roadmap
        roadmap_prompt = f"""Create a research roadmap for: {topics[0]}

Include short-term, medium-term, and long-term goals:"""
        
        roadmap = glm.generate(roadmap_prompt, max_tokens=400)
        
        # Complete
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
                "files_processed": len(pdf_paths)
            }
        })
        
    except Exception as e:
        logger.error(f"Auto-analysis failed for job {job_id}: {e}")
        _analysis_jobs[job_id].update({
            "status": "failed",
            "error": str(e),
            "message": f"Analysis failed: {str(e)}"
        })
