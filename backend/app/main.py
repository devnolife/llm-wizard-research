"""
FastAPI Application Entry Point for Research Recommendation System
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from loguru import logger
import os

from .api.routes import health, documents, papers, analysis
from .utils.config_loader import get_config

# Load configuration
config = get_config()

# Initialize FastAPI app
app = FastAPI(
    title="RAG-LLM Research Recommendation System",
    description="AI-powered research paper recommendation with GLM-4.6",
    version="0.1.0"
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(documents.router, prefix="/api", tags=["Documents"])
app.include_router(papers.router, prefix="/api/papers", tags=["Papers"])
app.include_router(analysis.router, prefix="/api", tags=["Analysis"])


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup"""
    logger.info("Starting RAG-LLM Research Recommendation System")
    
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


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down RAG-LLM Research Recommendation System")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=config.api.host,
        port=config.api.port,
        reload=config.api.reload,
        workers=config.api.workers
    )
