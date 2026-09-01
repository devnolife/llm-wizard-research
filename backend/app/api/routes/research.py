"""Endpoint pipeline penelitian (TAHAP 1-3 + rekomendasi).

Terpisah dari ``analysis.py`` yang melayani pipeline lama 8 tahap. Keduanya
berbagi ``job_store``, jadi status, event, dan artefak tetap dibaca lewat
``/api/analysis-status/{job_id}`` yang sudah ada — router ini hanya menambah
cara memulai job dan mendeskripsikan tahapannya untuk UI.
"""

from __future__ import annotations

import shutil
import threading
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from ...services.research_pipeline import RESEARCH_STAGES, run_research_pipeline
from ...utils.config_loader import get_config
from ...utils.job_store import record_job_event, save_job, update_job
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload

router = APIRouter()


def _embedder():
    """Pakai embedder milik vector store agar tidak memuat model kedua kali."""
    try:
        from ..dependencies import get_vector_store
        return getattr(get_vector_store(), "embedding_model", None)
    except Exception as exc:
        logger.warning(f"Embedder tidak tersedia, novelty memakai leksikal: {exc}")
        return None


def _run_in_background(job_id: str, pdf_paths: List[Path], out_dir: Path) -> None:
    try:
        run_research_pipeline(job_id, pdf_paths, out_dir, embedder=_embedder())
    except Exception as exc:
        logger.error(f"Pipeline penelitian {job_id} gagal: {exc}")


@router.get("/stages")
async def list_stages():
    """Deskripsi tahap agar UI bisa menggambar timeline sebelum job berjalan."""
    return {
        "stages": [
            {"key": key, "icon": icon, "title": title, "description": desc}
            for key, icon, title, desc in RESEARCH_STAGES
        ]
    }


@router.post("/start")
async def start_research(files: List[UploadFile] = File(...)):
    """Unggah PDF lalu jalankan pipeline penelitian di latar belakang."""
    config = get_config()
    allowed = {str(t).lower().lstrip(".") for t in config.data.allowed_file_types}
    if "pdf" not in allowed:
        raise HTTPException(status_code=415, detail="Unggahan PDF tidak diaktifkan")

    job_id = str(uuid.uuid4())
    job_dir = Path(config.data.raw_path) / "analysis_jobs" / job_id
    out_dir = Path(config.data.processed_path) / "research" / job_id
    pdf_paths: List[Path] = []
    try:
        job_dir.mkdir(parents=True, exist_ok=False)
        for index, file in enumerate(files):
            target = job_dir / f"{index:02d}_{sanitize_filename(file.filename)}"
            await write_validated_pdf_upload(file, target, config.data.max_file_size_mb)
            pdf_paths.append(target)
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        logger.error(f"Unggahan pipeline penelitian gagal: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))

    save_job(job_id, {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Menunggu pipeline penelitian dimulai",
        "created_at": time.time(),
        "pipeline": "research",
        "payload": {"pdf_paths": [str(p) for p in pdf_paths],
                    "input_dir": str(job_dir), "output_dir": str(out_dir)},
    })
    record_job_event(job_id, "job.created", status="queued",
                     data={"file_count": len(pdf_paths), "pipeline": "research"})

    # Thread biasa, bukan antrean analisis lama: worker itu hanya mengenali
    # pipeline 8 tahap. Konsekuensinya job menggantung bila proses direstart.
    threading.Thread(
        target=_run_in_background, args=(job_id, pdf_paths, out_dir), daemon=True,
    ).start()

    return {
        "success": True,
        "job_id": job_id,
        "files_count": len(pdf_paths),
        "stages": [s[0] for s in RESEARCH_STAGES],
        "message": "Pipeline penelitian dimulai. Pantau lewat /api/analysis-status/{job_id}.",
    }
