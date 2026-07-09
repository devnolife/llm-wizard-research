"""
Tiny JSON-backed job status store for analysis jobs.
"""

import json
import os
from copy import deepcopy
from pathlib import Path
from threading import Lock
from typing import Any

from loguru import logger

from .config_loader import get_config


_LOCK = Lock()
_JOBS: dict[str, dict[str, Any]] = {}
_STORE_PATH: Path | None = None
_ACTIVE_STATUSES = {"processing", "running", "queued", "started"}
_INTERRUPTED_MESSAGE = "Server di-restart saat analisis berjalan"


def _default_store_path() -> Path:
    data_dir = Path(get_config().data.processed_path or "./data")
    return data_dir / "analysis_jobs.json"


def _resolve_store_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else _default_store_path()


def _write_jobs_locked() -> None:
    if _STORE_PATH is None:
        return

    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = _STORE_PATH.with_name(f".{_STORE_PATH.name}.{os.getpid()}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(_JOBS, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, _STORE_PATH)


def load_jobs(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load jobs from disk and mark in-flight jobs as interrupted."""
    global _STORE_PATH, _JOBS

    store_path = _resolve_store_path(path)
    changed = False
    with _LOCK:
        _STORE_PATH = store_path
        try:
            if store_path.exists():
                with open(store_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                _JOBS = data if isinstance(data, dict) else {}
            else:
                _JOBS = {}
        except Exception as e:
            logger.warning(f"Failed to load analysis job store {store_path}: {e}")
            _JOBS = {}

        for job in _JOBS.values():
            if isinstance(job, dict) and job.get("status") in _ACTIVE_STATUSES:
                job.update({
                    "status": "interrupted",
                    "error": _INTERRUPTED_MESSAGE,
                    "message": _INTERRUPTED_MESSAGE,
                })
                changed = True

        if changed:
            _write_jobs_locked()

        return deepcopy(_JOBS)


def save_job(job_id: str, job: dict[str, Any]) -> None:
    """Persist a single job update."""
    global _STORE_PATH

    with _LOCK:
        if _STORE_PATH is None:
            _STORE_PATH = _default_store_path()
        _JOBS[job_id] = deepcopy(job)
        _write_jobs_locked()


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return a persisted job by id."""
    with _LOCK:
        job = _JOBS.get(job_id)
        return deepcopy(job) if job is not None else None
