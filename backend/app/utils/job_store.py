"""Durable local storage for analysis jobs and chat sessions.

The initial prototype wrote the complete job map to a JSON file.  That was
adequate for a single request, but could not atomically claim work, preserve
conversations, or recover queued work after a restart.  This module keeps the
same small public API (``load_jobs``, ``save_job`` and ``get_job``) while using
SQLite by default.  A JSON path is still supported for legacy callers and for
one-time migration of old job files.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from copy import deepcopy
from pathlib import Path
from threading import RLock
from typing import Any, Iterable

from loguru import logger

from .config_loader import get_config


_LOCK = RLock()
_JOBS: dict[str, dict[str, Any]] = {}
_STORE_PATH: Path | None = None
_LEGACY_MODE = False
_ACTIVE_STATUSES = {"processing", "running", "queued", "started"}
_TERMINAL_STATUSES = {"completed", "failed", "cancelled"}
_INTERRUPTED_MESSAGE = "Server di-restart saat analisis berjalan"
_SENSITIVE_EVENT_KEYS = {
    "content", "document", "documents", "message", "messages", "prompt",
    "query", "raw", "response", "text", "traceback",
}


def _default_store_path() -> Path:
    data_dir = Path(get_config().data.processed_path or "./data")
    return data_dir / "analysis_jobs.sqlite3"


def _resolve_store_path(path: str | Path | None = None) -> Path:
    return Path(path) if path is not None else _default_store_path()


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


def _json_loads(value: str | None, fallback: Any) -> Any:
    if not value:
        return deepcopy(fallback)
    try:
        return json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return deepcopy(fallback)


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, isolation_level=None, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=30000")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            job_id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            progress REAL NOT NULL DEFAULT 0,
            message TEXT NOT NULL DEFAULT '',
            error TEXT,
            attempt INTEGER NOT NULL DEFAULT 0,
            max_attempts INTEGER NOT NULL DEFAULT 2,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            available_at REAL NOT NULL DEFAULT 0,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            completed_at REAL,
            revision INTEGER NOT NULL DEFAULT 0,
            graph_json TEXT,
            data_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_claim
            ON jobs(status, cancel_requested, available_at, created_at);

        CREATE TABLE IF NOT EXISTS job_events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            phase TEXT,
            status TEXT,
            duration_ms INTEGER,
            created_at REAL NOT NULL,
            data_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_job_events_job ON job_events(job_id, event_id);

        CREATE TABLE IF NOT EXISTS conversations (
            conversation_id TEXT PRIMARY KEY,
            created_at REAL NOT NULL,
            updated_at REAL NOT NULL,
            expires_at REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS conversation_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at REAL NOT NULL,
            FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id)
                ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_conversation_messages
            ON conversation_messages(conversation_id, message_id);
        """
    )


def _row_to_job(row: sqlite3.Row) -> dict[str, Any]:
    job = _json_loads(row["data_json"], {})
    job.update(
        {
            "job_id": row["job_id"],
            "status": row["status"],
            "progress": row["progress"],
            "message": row["message"],
            "error": row["error"],
            "attempt": row["attempt"],
            "max_attempts": row["max_attempts"],
            "cancel_requested": bool(row["cancel_requested"]),
            "available_at": row["available_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "completed_at": row["completed_at"],
            "revision": row["revision"],
        }
    )
    if row["graph_json"]:
        job["graph_snapshot"] = _json_loads(row["graph_json"], {})
    return job


def _persist_job(conn: sqlite3.Connection, job_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
    now = time.time()
    existing = _row_to_job(row) if row else {}
    job = {**existing, **deepcopy(updates), "job_id": job_id}
    job.setdefault("status", "queued")
    job.setdefault("progress", 0)
    job.setdefault("message", "")
    job.setdefault("error", None)
    job.setdefault("attempt", 0)
    job.setdefault("max_attempts", 2)
    job.setdefault("cancel_requested", False)
    job.setdefault("available_at", now)
    job.setdefault("created_at", now)
    job["updated_at"] = now
    job["revision"] = int(existing.get("revision", 0)) + 1
    if job["status"] in _TERMINAL_STATUSES and not job.get("completed_at"):
        job["completed_at"] = now
    elif job["status"] not in _TERMINAL_STATUSES:
        job["completed_at"] = None

    graph_snapshot = job.get("graph_snapshot")
    conn.execute(
        """
        INSERT INTO jobs (
            job_id, status, progress, message, error, attempt, max_attempts,
            cancel_requested, available_at, created_at, updated_at, completed_at,
            revision, graph_json, data_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
            status=excluded.status,
            progress=excluded.progress,
            message=excluded.message,
            error=excluded.error,
            attempt=excluded.attempt,
            max_attempts=excluded.max_attempts,
            cancel_requested=excluded.cancel_requested,
            available_at=excluded.available_at,
            updated_at=excluded.updated_at,
            completed_at=excluded.completed_at,
            revision=excluded.revision,
            graph_json=excluded.graph_json,
            data_json=excluded.data_json
        """,
        (
            job_id,
            job["status"],
            float(job.get("progress") or 0),
            str(job.get("message") or ""),
            job.get("error"),
            int(job.get("attempt") or 0),
            max(1, int(job.get("max_attempts") or 2)),
            int(bool(job.get("cancel_requested"))),
            float(job.get("available_at") or now),
            float(job.get("created_at") or now),
            now,
            job.get("completed_at"),
            int(job["revision"]),
            _json_dumps(graph_snapshot) if graph_snapshot is not None else None,
            _json_dumps(job),
        ),
    )
    return deepcopy(job)


def _legacy_load(path: Path) -> dict[str, dict[str, Any]]:
    global _JOBS
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle)
            _JOBS = data if isinstance(data, dict) else {}
        else:
            _JOBS = {}
    except Exception as exc:
        logger.warning(f"Failed to load legacy analysis job store {path}: {exc}")
        _JOBS = {}

    changed = False
    for job in _JOBS.values():
        if isinstance(job, dict) and job.get("status") in _ACTIVE_STATUSES:
            job.update(
                {
                    "status": "interrupted",
                    "error": _INTERRUPTED_MESSAGE,
                    "message": _INTERRUPTED_MESSAGE,
                }
            )
            changed = True
    if changed:
        _legacy_write(path)
    return deepcopy(_JOBS)


def _legacy_write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(_JOBS, handle, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp_path, path)


def _migrate_legacy_json(conn: sqlite3.Connection, sqlite_path: Path) -> None:
    legacy_path = sqlite_path.with_name("analysis_jobs.json")
    if not legacy_path.exists():
        return
    if conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]:
        return
    try:
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return
        conn.execute("BEGIN IMMEDIATE")
        for job_id, job in data.items():
            if isinstance(job, dict):
                if job.get("status") in _ACTIVE_STATUSES:
                    job = {
                        **job,
                        "status": "queued",
                        "message": _INTERRUPTED_MESSAGE,
                        "error": None,
                    }
                _persist_job(conn, str(job_id), job)
        conn.commit()
        archive_path = legacy_path.with_suffix(".json.migrated")
        legacy_path.replace(archive_path)
        logger.info(f"Migrated legacy analysis jobs to {sqlite_path}")
    except Exception as exc:
        conn.rollback()
        logger.warning(f"Could not migrate legacy job store {legacy_path}: {exc}")


def _ensure_sqlite(path: Path | None = None) -> Path:
    global _STORE_PATH, _LEGACY_MODE
    target = path or _STORE_PATH or _default_store_path()
    if target.suffix.lower() == ".json":
        raise ValueError("SQLite job operations require a .sqlite or .sqlite3 path")
    _STORE_PATH = target
    _LEGACY_MODE = False
    with _connect(target) as conn:
        _ensure_schema(conn)
        _migrate_legacy_json(conn, target)
    return target


def load_jobs(path: str | Path | None = None) -> dict[str, dict[str, Any]]:
    """Load durable jobs, requeue work interrupted by a previous process.

    Passing a ``.json`` path retains the original compatibility behavior.  The
    no-argument production path is SQLite and requeues unfinished work for the
    local job processor rather than silently discarding it.
    """
    global _STORE_PATH, _LEGACY_MODE, _JOBS
    store_path = Path(path) if path is not None else (_STORE_PATH or _default_store_path())
    with _LOCK:
        _STORE_PATH = store_path
        _LEGACY_MODE = store_path.suffix.lower() == ".json"
        if _LEGACY_MODE:
            return _legacy_load(store_path)

        target = _ensure_sqlite(store_path)
        with _connect(target) as conn:
            conn.execute("BEGIN IMMEDIATE")
            now = time.time()
            conn.execute(
                """
                UPDATE jobs
                SET status='queued', message=?, error=NULL, available_at=?,
                    updated_at=?, revision=revision+1
                WHERE status IN ('processing', 'running', 'started')
                  AND cancel_requested=0
                """,
                (_INTERRUPTED_MESSAGE, now, now),
            )
            conn.execute(
                """
                UPDATE jobs
                SET status='cancelled', message='Job dibatalkan sebelum server restart',
                    completed_at=?, updated_at=?, revision=revision+1
                WHERE status IN ('processing', 'running', 'started')
                  AND cancel_requested=1
                """,
                (now, now),
            )
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
            conn.commit()
        _JOBS = {row["job_id"]: _row_to_job(row) for row in rows}
        return deepcopy(_JOBS)


def save_job(job_id: str, job: dict[str, Any]) -> None:
    """Persist a job update, preserving unknown response fields for compatibility."""
    with _LOCK:
        if _LEGACY_MODE:
            if _STORE_PATH is None:
                raise RuntimeError("Legacy job store was not initialized")
            _JOBS[job_id] = deepcopy(job)
            _legacy_write(_STORE_PATH)
            return
        target = _ensure_sqlite()
        with _connect(target) as conn:
            conn.execute("BEGIN IMMEDIATE")
            persisted = _persist_job(conn, job_id, job)
            conn.commit()
        _JOBS[job_id] = persisted


def update_job(job_id: str, **updates: Any) -> dict[str, Any] | None:
    """Atomically merge changes into a persisted job and return its new state."""
    with _LOCK:
        if _LEGACY_MODE:
            current = _JOBS.get(job_id)
            if current is None:
                return None
            current = {**current, **updates}
            save_job(job_id, current)
            return deepcopy(current)
        target = _ensure_sqlite()
        with _connect(target) as conn:
            conn.execute("BEGIN IMMEDIATE")
            if not conn.execute("SELECT 1 FROM jobs WHERE job_id = ?", (job_id,)).fetchone():
                conn.rollback()
                return None
            job = _persist_job(conn, job_id, updates)
            conn.commit()
        _JOBS[job_id] = job
        return deepcopy(job)


def get_job(job_id: str) -> dict[str, Any] | None:
    """Return a persisted job by ID."""
    with _LOCK:
        if _LEGACY_MODE:
            job = _JOBS.get(job_id)
            return deepcopy(job) if job is not None else None
        target = _ensure_sqlite()
        with _connect(target) as conn:
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        job = _row_to_job(row)
        _JOBS[job_id] = job
        return deepcopy(job)


def list_jobs(statuses: Iterable[str] | None = None) -> list[dict[str, Any]]:
    """Return jobs ordered from newest to oldest."""
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            if statuses:
                values = tuple(statuses)
                placeholders = ",".join("?" for _ in values)
                rows = conn.execute(
                    f"SELECT * FROM jobs WHERE status IN ({placeholders}) ORDER BY created_at DESC", values
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        return [_row_to_job(row) for row in rows]


def claim_next_job() -> dict[str, Any] | None:
    """Atomically claim the next ready job for one local worker."""
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            conn.execute("BEGIN IMMEDIATE")
            now = time.time()
            row = conn.execute(
                """
                SELECT * FROM jobs
                WHERE status='queued' AND cancel_requested=0 AND available_at <= ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (now,),
            ).fetchone()
            if row is None:
                conn.commit()
                return None
            job = _row_to_job(row)
            if int(job.get("attempt", 0)) >= int(job.get("max_attempts", 2)):
                job.update(
                    {
                        "status": "failed",
                        "error": "Maximum job retry attempts exceeded",
                        "message": "Analisis gagal setelah batas percobaan tercapai",
                    }
                )
                _persist_job(conn, job["job_id"], job)
                conn.commit()
                return None
            job.update(
                {
                    "status": "running",
                    "message": "Analisis sedang diproses...",
                    "attempt": int(job.get("attempt", 0)) + 1,
                    "cancel_requested": False,
                }
            )
            claimed = _persist_job(conn, job["job_id"], job)
            conn.execute(
                """
                INSERT INTO job_events (job_id, event_type, status, created_at, data_json)
                VALUES (?, 'job.claimed', 'running', ?, '{}')
                """,
                (job["job_id"], now),
            )
            conn.commit()
        _JOBS[claimed["job_id"]] = claimed
        return deepcopy(claimed)


def request_cancel(job_id: str) -> dict[str, Any] | None:
    """Request cooperative cancellation for a queued or running job."""
    job = get_job(job_id)
    if job is None or job.get("status") in _TERMINAL_STATUSES:
        return job
    if job.get("status") == "queued":
        return update_job(
            job_id,
            status="cancelled",
            cancel_requested=True,
            message="Analisis dibatalkan sebelum diproses",
        )
    return update_job(
        job_id,
        cancel_requested=True,
        message="Permintaan pembatalan diterima; menunggu fase saat ini selesai",
    )


def retry_job(job_id: str, delay_seconds: float = 0) -> dict[str, Any] | None:
    """Requeue a terminal job when its persistent input payload is available."""
    job = get_job(job_id)
    if job is None or job.get("status") not in {"failed", "cancelled", "interrupted"}:
        return None
    payload = job.get("payload") or {}
    if not payload.get("pdf_paths"):
        return None
    return update_job(
        job_id,
        status="queued",
        progress=0,
        error=None,
        cancel_requested=False,
        available_at=time.time() + max(0, delay_seconds),
        message="Analisis dijadwalkan ulang",
        results=None,
        graph_snapshot=None,
    )


def is_cancel_requested(job_id: str) -> bool:
    job = get_job(job_id)
    return bool(job and job.get("cancel_requested"))


def record_job_event(
    job_id: str,
    event_type: str,
    *,
    phase: str | None = None,
    status: str | None = None,
    duration_ms: int | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Persist metadata-only telemetry for a job event."""
    safe_data = _sanitize_event_data(data or {})
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            conn.execute(
                """
                INSERT INTO job_events (job_id, event_type, phase, status, duration_ms, created_at, data_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, event_type, phase, status, duration_ms, time.time(), _json_dumps(safe_data)),
            )


def get_job_events(job_id: str, after_event_id: int = 0) -> list[dict[str, Any]]:
    """Return ordered metadata-only events for SSE and diagnostics."""
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            rows = conn.execute(
                """
                SELECT * FROM job_events WHERE job_id = ? AND event_id > ?
                ORDER BY event_id ASC
                """,
                (job_id, after_event_id),
            ).fetchall()
    return [
        {
            "id": row["event_id"],
            "type": row["event_type"],
            "phase": row["phase"],
            "status": row["status"],
            "duration_ms": row["duration_ms"],
            "created_at": row["created_at"],
            "data": _json_loads(row["data_json"], {}),
        }
        for row in rows
    ]


def get_latest_completed_job() -> dict[str, Any] | None:
    """Return the latest completed job with a persisted result snapshot."""
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            row = conn.execute(
                """
                SELECT * FROM jobs WHERE status='completed'
                ORDER BY completed_at DESC, updated_at DESC LIMIT 1
                """
            ).fetchone()
    return _row_to_job(row) if row else None


def set_job_graph(job_id: str, graph_snapshot: dict[str, Any]) -> dict[str, Any] | None:
    """Persist a serializable graph snapshot alongside a completed job."""
    return update_job(job_id, graph_snapshot=graph_snapshot)


def get_job_graph(job_id: str) -> dict[str, Any] | None:
    job = get_job(job_id)
    return deepcopy(job.get("graph_snapshot")) if job and job.get("graph_snapshot") else None


def get_conversation_messages(conversation_id: str, limit: int = 10) -> list[dict[str, str]]:
    """Load the newest conversation window in chronological order."""
    if not conversation_id:
        return []
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            now = time.time()
            conversation = conn.execute(
                """
                SELECT 1 FROM conversations WHERE conversation_id = ? AND expires_at > ?
                """,
                (conversation_id, now),
            ).fetchone()
            if not conversation:
                return []
            rows = conn.execute(
                """
                SELECT role, content FROM conversation_messages
                WHERE conversation_id = ? ORDER BY message_id DESC LIMIT ?
                """,
                (conversation_id, max(1, limit)),
            ).fetchall()
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]


def append_conversation_message(
    conversation_id: str,
    role: str,
    content: str,
    ttl_days: int = 30,
) -> None:
    """Append a chat message without emitting it to telemetry or regular logs."""
    if not conversation_id:
        raise ValueError("conversation_id is required")
    now = time.time()
    expires_at = now + max(1, ttl_days) * 86400
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                """
                INSERT INTO conversations (conversation_id, created_at, updated_at, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    updated_at=excluded.updated_at, expires_at=excluded.expires_at
                """,
                (conversation_id, now, now, expires_at),
            )
            conn.execute(
                """
                INSERT INTO conversation_messages (conversation_id, role, content, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (conversation_id, role, content, now),
            )
            conn.commit()


def clear_conversation(conversation_id: str) -> bool:
    """Delete one chat session and all of its messages."""
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            cursor = conn.execute("DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,))
    return cursor.rowcount > 0


def cleanup_expired(retention_days: int = 30, telemetry_retention_days: int = 14) -> dict[str, Any]:
    """Delete expired records and return their persisted input directories."""
    now = time.time()
    job_cutoff = now - max(1, retention_days) * 86400
    event_cutoff = now - max(1, telemetry_retention_days) * 86400
    with _LOCK:
        target = _ensure_sqlite()
        with _connect(target) as conn:
            expired_conversations = conn.execute(
                "DELETE FROM conversations WHERE expires_at <= ?", (now,)
            ).rowcount
            expired_events = conn.execute(
                "DELETE FROM job_events WHERE created_at < ?", (event_cutoff,)
            ).rowcount
            rows = conn.execute(
                """
                SELECT job_id, data_json FROM jobs WHERE status IN ('completed', 'failed', 'cancelled')
                AND completed_at IS NOT NULL AND completed_at < ?
                """,
                (job_cutoff,),
            ).fetchall()
            input_dirs = []
            job_ids = []
            for row in rows:
                job_ids.append(row["job_id"])
                payload = _json_loads(row["data_json"], {}).get("payload", {})
                input_dir = payload.get("input_dir") if isinstance(payload, dict) else None
                if input_dir:
                    input_dirs.append(str(input_dir))
            expired_jobs = conn.execute(
                """
                DELETE FROM jobs WHERE status IN ('completed', 'failed', 'cancelled')
                AND completed_at IS NOT NULL AND completed_at < ?
                """,
                (job_cutoff,),
            ).rowcount
    return {
        "conversations": expired_conversations,
        "events": expired_events,
        "jobs": expired_jobs,
        "job_ids": job_ids,
        "input_dirs": input_dirs,
    }


def _sanitize_event_data(data: dict[str, Any]) -> dict[str, Any]:
    """Keep telemetry metadata-only even if a caller passes a broad payload."""
    safe: dict[str, Any] = {}
    for key, value in data.items():
        if key.lower() in _SENSITIVE_EVENT_KEYS:
            continue
        if isinstance(value, dict):
            safe[key] = _sanitize_event_data(value)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = value if not isinstance(value, str) else value[:160]
        elif isinstance(value, (list, tuple)):
            safe[key] = len(value)
        else:
            safe[key] = str(value)[:160]
    return safe
