"""
FastAPI Application Entry Point — Wizard Research

Neuro-Symbolic Agentic System for Synthesis Gap Detection
in Scientific Literature.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import os
import shutil

from .api.routes import health, documents, papers, analysis, graph
from .telemetry.recorder import telemetry_middleware
from .utils.config_loader import get_config, get_effective_config_summary

# Load configuration
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic"""
    # --- Startup ---
    logger.info("Starting Wizard Research API")
    effective = get_effective_config_summary()
    logger.info(
        "Runtime config: model={}, context_window={}, queue_workers={}, ocr_enabled={}",
        effective["llm"]["model_name"],
        effective["llm"]["context_window"],
        effective["queue"]["max_workers"],
        effective["ocr"]["enabled"],
    )

    # Create necessary directories
    os.makedirs(config.data.raw_path, exist_ok=True)
    os.makedirs(config.data.processed_path, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Pre-load critical components
    from .api.dependencies import get_document_processor, get_vector_store
    from .services.analysis_queue import get_analysis_queue
    from .utils import job_store
    try:
        get_vector_store()
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")

    if config.ocr.validate_service_on_startup and config.ocr.enabled:
        processor = get_document_processor()
        if processor.ocr_client is None or not processor.ocr_client.is_available():
            logger.warning("OCR is enabled but the configured service is unavailable")

    queue = get_analysis_queue()
    queue.start(analysis.process_auto_analysis)

    yield

    # --- Shutdown ---
    queue.stop(wait=True)
    cleanup = job_store.cleanup_expired(
        retention_days=config.queue.retention_days,
        telemetry_retention_days=config.telemetry.retention_days,
    )
    for job_id in cleanup.pop("job_ids", []):
        try:
            get_vector_store().delete_by_metadata({"analysis_job_id": job_id})
        except Exception as exc:
            logger.warning(f"Could not clean expired job chunks for {job_id}: {exc}")
    for input_dir in cleanup.pop("input_dirs", []):
        shutil.rmtree(input_dir, ignore_errors=True)
    logger.info(f"Expired local records cleaned: {cleanup}")
    logger.info("Shutting down Wizard Research API")


# Initialize FastAPI app
app = FastAPI(
    title="Wizard Research API",
    description="Neuro-Symbolic Agentic System for Synthesis Gap Detection in Scientific Literature",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend (whitelist from config)
if config.api.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.middleware("http")
async def add_request_telemetry(request, call_next):
    return await telemetry_middleware(request, call_next)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])
app.include_router(graph.router, prefix="/api", tags=["Knowledge Graph"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers
    )
