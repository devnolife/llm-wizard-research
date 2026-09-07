"""Endpoint pipeline penelitian (TAHAP 1-3 + rekomendasi).

Terpisah dari ``analysis.py`` yang melayani pipeline lama 8 tahap. Keduanya
berbagi ``job_store``, jadi status, event, dan artefak tetap dibaca lewat
``/api/analysis-status/{job_id}`` yang sudah ada — router ini hanya menambah
cara memulai job dan mendeskripsikan tahapannya untuk UI.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from loguru import logger

from ...core.pipeline.io import read_jsonl
from ...core.pipeline.pipeline import OCR_MODES, PipelineResult, process_pdf
from ...core.pipeline.token_chunker import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OVERLAP_RATIO,
    DEFAULT_TARGET_TOKENS,
)
from ...services.analysis_queue import get_analysis_queue
from ...services.research_pipeline import (
    PIPELINE_CONSTANTS,
    PIPELINE_NAME,
    RESEARCH_STAGES,
    SUBSTEPS,
    stage_source,
)
from ...utils.config_loader import get_config
from ...utils.job_store import (
    get_job,
    get_stage_artifacts,
    record_job_event,
    save_job,
    update_job,
)
from ...utils.upload_validation import sanitize_filename, write_validated_pdf_upload

router = APIRouter()

# Koleksi record yang bisa dibaca UI → (tahap pemilik artefak, kunci di outputs).
# Artefak di basis data hanya menyimpan 8 baris contoh; berkas inilah yang lengkap.
# Nama koleksi tidak selalu sama dengan tahap: ``candidates`` dan ``themes`` adalah
# berkas samping yang ditulis tahap gap_mining dan recommendation.
RECORD_SOURCES = {
    "chunking": ("chunking", "chunks_jsonl"),
    "gap_mining": ("gap_mining", "gaps_jsonl"),
    "candidates": ("gap_mining", "candidates_jsonl"),
    "novelty": ("novelty", "gaps_novelty_jsonl"),
    "recommendation": ("recommendation", "proposals_jsonl"),
    "themes": ("recommendation", "themes_jsonl"),
}

# Kolom yang boleh dipakai memfilter; daftar putih agar query sembarang ditolak.
PHASE_FACETS = {
    "chunking": ("source", "section_normalized", "extraction_quality"),
    "gap_mining": ("source", "gap_type", "topic"),
    "candidates": ("source", "section_normalized", "candidate_reason", "llm_answered"),
    "novelty": ("source", "novelty_status", "gap_type", "topic"),
    "recommendation": ("source", "topic", "band", "theme_id"),
    "themes": ("journal_support",),
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


def _record_path(job_id: str, collection: str) -> Path:
    """Berkas record lengkap satu koleksi, diambil dari artefak tahap pemiliknya."""
    if collection not in RECORD_SOURCES:
        raise HTTPException(status_code=404, detail=f"Koleksi tidak dikenal: {collection}")
    phase, key = RECORD_SOURCES[collection]
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
async def start_research(
    files: List[UploadFile] = File(...),
    until: str = Form(""),
    ocr_mode: str = Form("auto"),
):
    """Unggah PDF lalu jalankan pipeline penelitian di latar belakang.

    ``until`` (opsional) menghentikan job setelah tahap itu selesai — UI bertahap
    memakai ``gap_mining`` agar OpenAlex/rekomendasi belum dipanggil. ``ocr_mode``
    sama seperti pada ``chunk-preview``.
    """
    stage_keys = [s[0] for s in RESEARCH_STAGES]
    if until and until not in stage_keys:
        raise HTTPException(status_code=422, detail=f"until harus salah satu dari {stage_keys}")
    if ocr_mode not in OCR_MODES:
        raise HTTPException(status_code=422, detail=f"ocr_mode harus salah satu dari {list(OCR_MODES)}")
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
                    "input_dir": str(job_dir), "output_dir": str(out_dir),
                    "until": until or None, "ocr_mode": ocr_mode},
    })
    record_job_event(job_id, "job.created", status="queued",
                     data={"file_count": len(pdf_paths), "pipeline": PIPELINE_NAME,
                           "until": until or None})
    get_analysis_queue().notify()

    planned = stage_keys[: stage_keys.index(until) + 1] if until else stage_keys
    return {
        "success": True,
        "job_id": job_id,
        "files_count": len(pdf_paths),
        "stages": planned,
        "message": "Pipeline penelitian diantrekan. Pantau lewat /api/analysis-status/{job_id}.",
    }


@router.post("/{job_id}/continue")
async def continue_research(job_id: str, until: str = Form(""), novelty_limit: int = Form(0),
                            start_from: str = Form("")):
    """Lanjutkan job penelitian yang selesai ke tahap berikutnya.

    Job yang berhenti di ``gap_mining`` (UI bertahap) dilanjutkan ke ``novelty``
    atau ``recommendation`` memakai berkas keluaran yang sudah ada — gap mining
    (LLM, non-deterministik) tidak diulang, sehingga gap yang sudah dilihat
    pengguna tetap sama. ``novelty_limit`` > 0 membatasi jumlah gap yang dikirim
    ke OpenAlex (kuota gratis ≈ 100 pencarian/hari). ``start_from`` opsional boleh
    menunjuk tahap yang SUDAH selesai untuk mengulangnya (mis. cek ulang kebaruan
    setelah kuota pulih; hasil OpenAlex yang sudah ada dibaca dari cache).
    """
    stage_keys = [s[0] for s in RESEARCH_STAGES]
    job = get_job(job_id)
    if job is None or job.get("pipeline") != PIPELINE_NAME:
        raise HTTPException(status_code=404, detail="Job penelitian tidak ditemukan")
    if job.get("status") != "completed":
        raise HTTPException(status_code=409, detail=f"Job belum selesai (status: {job.get('status')})")
    done = [s for s in (job.get("stages_done") or []) if s in stage_keys]
    if not done:
        raise HTTPException(status_code=409, detail="Job ini tidak mencatat tahap yang selesai; jalankan ulang dari awal")
    next_index = max(stage_keys.index(s) for s in done) + 1
    if start_from:
        if start_from not in stage_keys or stage_keys.index(start_from) > next_index:
            raise HTTPException(
                status_code=422,
                detail=f"start_from harus tahap yang sudah selesai atau {stage_keys[next_index] if next_index < len(stage_keys) else 'tidak ada'}")
        if start_from == "chunking":
            raise HTTPException(status_code=422, detail="Mengulang chunking berarti job baru; unggah ulang PDF")
        first_index = stage_keys.index(start_from)
    else:
        if next_index >= len(stage_keys):
            raise HTTPException(status_code=409, detail="Semua tahap sudah selesai")
        first_index = next_index
    start_from = stage_keys[first_index]
    until = until or stage_keys[-1]
    if until not in stage_keys or stage_keys.index(until) < first_index:
        raise HTTPException(
            status_code=422,
            detail=f"until harus salah satu dari {stage_keys[first_index:]}")

    config = get_config()
    payload = dict(job.get("payload") or {})
    payload.update({"start_from": start_from, "until": until,
                    "novelty_limit": max(0, int(novelty_limit))})
    update_job(
        job_id,
        status="queued",
        progress=0.0,
        error=None,
        cancel_requested=False,
        attempt=0,  # manual action: fresh retry budget
        max_attempts=config.queue.max_attempts,
        available_at=time.time(),
        message=f"Menunggu worker untuk melanjutkan dari tahap {start_from}...",
        payload=payload,
    )
    record_job_event(job_id, "job.continued", status="queued",
                     data={"start_from": start_from, "until": until,
                           "novelty_limit": payload["novelty_limit"]})
    get_analysis_queue().notify()
    return {
        "success": True,
        "job_id": job_id,
        "start_from": start_from,
        "stages": stage_keys[first_index: stage_keys.index(until) + 1],
        "message": "Job dilanjutkan. Pantau lewat /api/analysis-status/{job_id}.",
    }


def _preview_payload(source: str, result: PipelineResult) -> Dict[str, Any]:
    """Bentuk respons satu PDF untuk chunk-preview: metadata + seluruh chunk."""
    chunks = [c.to_json_record() for c in result.chunks]
    return {
        "source": source,
        "meta": result.meta.to_dict(),
        "pages": result.num_pages,
        "extraction_method": result.extraction_method,
        "grobid_used": result.grobid_used,
        "num_chunks": len(chunks),
        "token_total": sum(c["token_count"] for c in chunks),
        "sections": dict(Counter(c["section_normalized"] for c in chunks)),
        "chunks": chunks,
    }


@router.post("/chunk-preview")
async def chunk_preview(files: List[UploadFile] = File(...), ocr_mode: str = Form("auto")):
    """TAHAP 1 saja: unggah PDF, kembalikan chunk-nya langsung.

    Tidak membuat job, tidak menyentuh antrean, LLM, maupun vector store —
    hanya ``process_pdf`` pada berkas sementara yang dihapus setelah selesai.
    Dipakai UI ringan untuk memperlihatkan hasil pemotongan sebelum analisis.
    ``ocr_mode=force`` memaksa pembacaan lewat ocrd (bawaan ``auto``: ocrd hanya
    untuk PDF yang teksnya buruk/hasil pindaian).
    """
    if ocr_mode not in OCR_MODES:
        raise HTTPException(status_code=422, detail=f"ocr_mode harus salah satu dari {list(OCR_MODES)}")
    config = get_config()
    allowed = {str(t).lower().lstrip(".") for t in config.data.allowed_file_types}
    if "pdf" not in allowed:
        raise HTTPException(status_code=415, detail="Unggahan PDF tidak diaktifkan")

    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="chunk-preview-") as tmp:
        for index, file in enumerate(files):
            source = sanitize_filename(file.filename)
            target = Path(tmp) / f"{index:02d}_{source}"
            await write_validated_pdf_upload(file, target, config.data.max_file_size_mb)
            try:
                # process_pdf is CPU-bound and synchronous; keep the event loop free
                result = await run_in_threadpool(
                    process_pdf, str(target), source=source, ocr_mode=ocr_mode
                )
            except Exception as exc:
                logger.error(f"chunk-preview gagal pada {source}: {exc}")
                results.append({"source": source, "error": str(exc)[:300], "chunks": []})
                continue
            results.append(_preview_payload(source, result))

    return {
        "files": results,
        "params": {
            "target_tokens": DEFAULT_TARGET_TOKENS,
            "max_tokens": DEFAULT_MAX_TOKENS,
            "overlap_ratio": DEFAULT_OVERLAP_RATIO,
            "ocr_mode": ocr_mode,
        },
    }
