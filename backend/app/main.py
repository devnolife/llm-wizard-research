"""
FastAPI Application Entry Point — Wizard Research

Neuro-Symbolic Agentic System for Synthesis Gap Detection
in Scientific Literature.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from loguru import logger
import os

from .api.routes import health, documents, papers, analysis, graph
from .utils.config_loader import get_config

# Load configuration
config = get_config()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown logic"""
    # --- Startup ---
    logger.info("Starting Wizard Research API")

    # Create necessary directories
    os.makedirs(config.data.raw_path, exist_ok=True)
    os.makedirs(config.data.processed_path, exist_ok=True)
    os.makedirs("logs", exist_ok=True)

    # Pre-load critical components
    from .api.dependencies import get_vector_store
    try:
        get_vector_store()
        logger.info("Vector store initialized")
    except Exception as e:
        logger.error(f"Failed to initialize vector store: {e}")

    yield

    # --- Shutdown ---
    logger.info("Shutting down Wizard Research API")


# Initialize FastAPI app
app = FastAPI(
    title="Wizard Research API",
    description="Neuro-Symbolic Agentic System for Synthesis Gap Detection in Scientific Literature",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS middleware for React frontend (whitelist from config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
