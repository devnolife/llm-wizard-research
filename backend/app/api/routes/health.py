"""
Health check, models, and system status endpoints
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path
from pydantic import BaseModel
from loguru import logger
import os
import subprocess
import time

import psutil

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


def _int_or(value: str, fallback: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return fallback


def _collect_gpu_stats() -> list[dict]:
    """Per-GPU memory/utilization/temperature + compute processes via nvidia-smi."""
    try:
        query = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if query.returncode != 0:
        return []

    gpus: dict[str, dict] = {}
    for line in query.stdout.strip().splitlines():
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 7:
            continue
        index, uuid, name, mem_used, mem_total, util, temp = parts[:7]
        gpus[uuid] = {
            "index": _int_or(index),
            "name": name,
            "memory_used_mb": _int_or(mem_used),
            "memory_total_mb": _int_or(mem_total),
            "utilization_percent": _int_or(util),
            "temperature_c": _int_or(temp),
            "processes": [],
        }

    try:
        apps = subprocess.run(
            [
                "nvidia-smi",
                "--query-compute-apps=gpu_uuid,pid,used_memory,process_name",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if apps.returncode == 0:
            for line in apps.stdout.strip().splitlines():
                parts = [part.strip() for part in line.split(",")]
                if len(parts) < 4 or parts[0] not in gpus:
                    continue
                pid = _int_or(parts[1])
                user = ""
                try:
                    user = psutil.Process(pid).username()
                except (psutil.Error, OSError):
                    pass
                gpus[parts[0]]["processes"].append({
                    "pid": pid,
                    "user": user,
                    "memory_mb": _int_or(parts[2]),
                    "name": Path(",".join(parts[3:])).name,
                })
    except (OSError, subprocess.TimeoutExpired):
        pass

    return sorted(gpus.values(), key=lambda gpu: gpu["index"])


@router.get("/api/system-stats")
def get_system_stats():
    """Pemakaian server saat ini: CPU, RAM, swap, disk, dan detail per-GPU.

    Sync ``def`` (bukan async) supaya sampling psutil/nvidia-smi berjalan di
    threadpool dan tidak memblokir event loop.
    """
    cpu_percent = psutil.cpu_percent(interval=0.2)
    load1, load5, load15 = os.getloadavg()
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    disk = psutil.disk_usage(str(Path(__file__).resolve().parents[4]))

    return {
        "timestamp": time.time(),
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count() or 0,
            "load_avg": [round(load1, 2), round(load5, 2), round(load15, 2)],
        },
        "memory": {
            "total_mb": memory.total // (1024 * 1024),
            "used_mb": memory.used // (1024 * 1024),
            "available_mb": memory.available // (1024 * 1024),
            "percent": memory.percent,
        },
        "swap": {
            "total_mb": swap.total // (1024 * 1024),
            "used_mb": swap.used // (1024 * 1024),
            "percent": swap.percent,
        },
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 1),
            "used_gb": round(disk.used / (1024 ** 3), 1),
            "percent": disk.percent,
        },
        "gpus": _collect_gpu_stats(),
    }


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
