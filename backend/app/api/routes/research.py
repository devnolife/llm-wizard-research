"""Endpoint pipeline penelitian (TAHAP 1-3 + rekomendasi).

Terpisah dari ``analysis.py`` yang melayani pipeline lama 8 tahap. Keduanya
berbagi ``job_store``, jadi status, event, dan artefak tetap dibaca lewat
``/api/analysis-status/{job_id}`` yang sudah ada — router ini hanya menambah
cara memulai job dan mendeskripsikan tahapannya untuk UI.
"""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import List

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from loguru import logger

from ...core.pipeline.io import read_jsonl
from ...services.analysis_queue import get_analysis_queue
from ...services.research_pipeline import (
    PIPELINE_CONSTANTS,
    PIPELINE_NAME,
    RESEARCH_STAGES,
    SUBSTEPS,
    stage_source,
)
from ...utils.config_loader import get_config
from ...utils.job_store import get_stage_artifacts, record_job_event, save_job
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload

router = APIRouter()

# Berkas keluaran yang memuat data lengkap tiap tahap. Artefak di basis data
# hanya menyimpan 8 baris contoh; UI membaca berkas ini untuk menampilkan semua.
PHASE_RECORD_FILE = {
    "chunking": "chunks_jsonl",
    "gap_mining": "gaps_jsonl",
    "novelty": "gaps_novelty_jsonl",
    "recommendation": "proposals_jsonl",
}

# Kolom yang boleh dipakai memfilter; daftar putih agar query sembarang ditolak.
PHASE_FACETS = {
    "chunking": ("source", "section_normalized", "extraction_quality"),
    "gap_mining": ("source", "gap_type", "topic"),
    "novelty": ("source", "novelty_status", "gap_type", "topic"),
    "recommendation": ("source", "topic", "band", "theme_id"),
}

MAX_PAGE = 500


@router.get("/stages")
async def list_stages():
    """Deskripsi tahap, sub-langkahnya, dan konstanta yang dipakai.

    UI menggambar timeline dan peta proses dari sini sebelum job berjalan;
    ``substeps[*].key`` sama dengan ``data.substep`` pada event ``substep.*``.
    """
    return {
        "stages": [
            {"key": key, "icon": icon, "title": title, "description": desc,
             "substeps": SUBSTEPS.get(key, []),
             "constants": PIPELINE_CONSTANTS.get(key, {})}
            for key, icon, title, desc in RESEARCH_STAGES
        ]
    }


@router.get("/stages/{stage_key}/source")
async def stage_source_code(stage_key: str):
    """Kode Python yang benar-benar dieksekusi tahap ini."""
    if stage_key not in {s[0] for s in RESEARCH_STAGES}:
        raise HTTPException(status_code=404, detail=f"Tahap tidak dikenal: {stage_key}")
    return {"stage": stage_key, "functions": stage_source(stage_key)}


def _record_path(job_id: str, phase: str) -> Path:
    """Berkas keluaran lengkap satu tahap, diambil dari artefak job."""
    key = PHASE_RECORD_FILE.get(phase)
    if key is None:
        raise HTTPException(status_code=404, detail=f"Tahap tidak dikenal: {phase}")
    for art in reversed(get_stage_artifacts(job_id, phase)):
        if art.get("kind") != "result":
            continue
        raw = ((art.get("payload") or {}).get("outputs") or {}).get(key)
        if not raw:
            raise HTTPException(
                status_code=404,
                detail=f"Job ini tidak menyimpan '{key}'. Berkas tersebut baru "
                       "ditulis oleh run setelah pembaruan; jalankan ulang analisis.")
        path = Path(raw)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Berkas hilang: {path.name}")
        return path
    raise HTTPException(status_code=404, detail=f"Tahap '{phase}' belum selesai pada job ini")


@router.get("/{job_id}/records/{phase}")
async def stage_records(job_id: str, phase: str, request: Request,
                        q: str = "", offset: int = 0, limit: int = 100):
    """Seluruh record satu tahap, bisa dicari dan difilter."""
    records = [r for r in read_jsonl(str(_record_path(job_id, phase)))
               if r.get("record") != "meta"]
    total = len(records)

    fields = PHASE_FACETS.get(phase, ())
    facets = {
        f: sorted({str(r[f]) for r in records if r.get(f) not in (None, "")})
        for f in fields
    }
    for field in fields:
        wanted = request.query_params.get(field)
        if wanted:
            records = [r for r in records if str(r.get(field)) == wanted]

    if q:
        needle = q.lower()
        records = [r for r in records
                   if needle in json.dumps(r, ensure_ascii=False).lower()]

    limit = max(1, min(limit, MAX_PAGE))
    offset = max(0, offset)
    return {
        "phase": phase,
        "total": total,
        "filtered": len(records),
        "offset": offset,
        "limit": limit,
        "facets": facets,
        "records": records[offset:offset + limit],
    }


@router.get("/{job_id}/fulltext")
async def journal_fulltext(job_id: str, source: str = ""):
    """Teks hasil ekstraksi satu jurnal, disusun ulang dari chunk berurutan.

    Bukan salinan mentah PDF: inilah teks yang benar-benar masuk ke tahap
    berikutnya, jadi batas antar chunk sengaja tetap terlihat.
    """
    chunks = [r for r in read_jsonl(str(_record_path(job_id, "chunking")))
              if r.get("record") != "meta"]
    journals: dict[str, dict] = {}
    for c in chunks:
        entry = journals.setdefault(c.get("source", "?"), {
            "source": c.get("source"), "title": c.get("paper_title"),
            "year": c.get("year"), "language": c.get("language"),
            "extraction_quality": c.get("extraction_quality"), "chunks": 0,
        })
        entry["chunks"] += 1

    if not source:
        return {"journals": sorted(journals.values(), key=lambda j: str(j["source"]))}
    if source not in journals:
        raise HTTPException(status_code=404, detail=f"Jurnal tidak ada di job ini: {source}")

    selected = sorted((c for c in chunks if c.get("source") == source),
                      key=lambda c: c.get("chunk_index", 0))
    return {"journal": journals[source], "chunks": selected}


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

    # Job diantrekan seperti analisis lama; antrean memilih handler dari field
    # ``pipeline`` (``AnalysisJobQueue.register``). Dengan itu job ini ikut
    # dibatasi jumlah worker, bisa dibatalkan/diretry, dan dipulihkan setelah
    # restart — dulu ia berjalan di thread lepas sehingga menggantung bila proses
    # direstart, atau malah diklaim worker lama sebagai analisis 8 tahap.
    save_job(job_id, {
        "job_id": job_id,
        "status": "queued",
        "progress": 0.0,
        "message": "Menunggu worker analisis...",
        "created_at": time.time(),
        "max_attempts": config.queue.max_attempts,
        "pipeline": PIPELINE_NAME,
        "payload": {"pdf_paths": [str(p) for p in pdf_paths],
                    "input_dir": str(job_dir), "output_dir": str(out_dir)},
    })
    record_job_event(job_id, "job.created", status="queued",
                     data={"file_count": len(pdf_paths), "pipeline": PIPELINE_NAME})
    get_analysis_queue().notify()

    return {
        "success": True,
        "job_id": job_id,
        "files_count": len(pdf_paths),
        "stages": [s[0] for s in RESEARCH_STAGES],
        "message": "Pipeline penelitian diantrekan. Pantau lewat /api/analysis-status/{job_id}.",
    }
