"""
Health check, models, and system status endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from pydantic import BaseModel
from loguru import logger
import os

from ...models.responses import HealthResponse
from ..dependencies import get_glm_interface, get_vector_store

router = APIRouter()


class ModelSwitchRequest(BaseModel):
    model_name: str


@router.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend HTML"""
    static_dir = Path(__file__).parent.parent.parent.parent.parent / "static"
    index_file = static_dir / "index.html"
    
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return HTMLResponse("""
        <html>
            <head><title>Wizard Research</title></head>
            <body>
                <h1>RAG-LLM Research Recommendation System</h1>
                <p>Version: 0.1.0</p>
                <p><a href="/docs">API Documentation</a></p>
            </body>
        </html>
        """)


@router.get("/api/sources/status")
async def get_api_sources_status():
    """Check which API sources have valid keys configured"""
    return {
        "core": bool(os.getenv("CORE_API_KEY")),
        "semantic_scholar": bool(os.getenv("SEMANTIC_SCHOLAR_API_KEY")),
        "pubmed": bool(os.getenv("PUBMED_API_KEY")),
        "crossref": bool(os.getenv("CROSSREF_EMAIL")),
        "arxiv": True
    }


@router.get("/api/models")
async def list_models():
    """List available Ollama models"""
    glm = get_glm_interface()
    models = glm.list_available_models()
    return {
        "models": models,
        "current": glm.config.model_name,
    }


@router.post("/api/models/switch")
async def switch_model(req: ModelSwitchRequest):
    """Switch the active Ollama model"""
    glm = get_glm_interface()
    available = glm.list_available_models()
    names = [m["name"] for m in available]
    if req.model_name not in names:
        raise HTTPException(status_code=404, detail=f"Model '{req.model_name}' not found. Available: {names}")
    glm.switch_model(req.model_name)
    return {"status": "ok", "model": req.model_name}


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    components_status = {}
    
    try:
        glm = get_glm_interface()
        glm_health = await glm.health_check()
        components_status["glm"] = glm_health.get("status") == "healthy"
    except Exception as e:
        logger.error(f"GLM health check failed: {e}")
        components_status["glm"] = False
    
    try:
        vector_store = get_vector_store()
        components_status["vector_store"] = vector_store.count() >= 0
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
        components_status["vector_store"] = False
    
    all_healthy = all(components_status.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        components=components_status,
        version="0.1.0"
    )
