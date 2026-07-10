"""Local durable analysis queue backed by :mod:`app.utils.job_store`.

The application intentionally stays single-host for thesis deployment.  SQLite
coordinates a small number of worker threads without requiring Redis, Celery,
or a separate process supervisor.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Callable

from loguru import logger

from ..utils import job_store
from ..utils.config_loader import get_config


JobHandler = Callable[[str], None]


class AnalysisJobQueue:
    """Claim queued jobs atomically and execute at most ``max_workers`` locally."""

    def __init__(self, max_workers: int = 2, poll_interval: float = 0.5):
        self.max_workers = max(1, max_workers)
        self.poll_interval = max(0.1, poll_interval)
        self._executor: ThreadPoolExecutor | None = None
        self._thread: threading.Thread | None = None
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._futures: set[Future[None]] = set()
        self._handler: JobHandler | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self, handler: JobHandler) -> None:
        """Recover durable jobs and start the local queue supervisor once."""
        with self._lock:
            if self.running:
                return
            self._handler = handler
            self._stop.clear()
            job_store.load_jobs()
            self._executor = ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="analysis-job",
            )
            self._thread = threading.Thread(
                target=self._run,
                name="analysis-queue-supervisor",
                daemon=True,
            )
            self._thread.start()
            self.notify()
            logger.info(f"Analysis job queue started with {self.max_workers} workers")

    def stop(self, wait: bool = True) -> None:
        """Stop claiming new jobs and optionally wait for active jobs to finish."""
        with self._lock:
            self._stop.set()
            self._wake.set()
            supervisor = self._thread
            executor = self._executor
        if supervisor and wait:
            supervisor.join(timeout=5)
        if executor:
            executor.shutdown(wait=wait, cancel_futures=False)
        with self._lock:
            self._thread = None
            self._executor = None
            self._futures.clear()
        logger.info("Analysis job queue stopped")

    def notify(self) -> None:
        """Wake the supervisor immediately after a job is queued or retried."""
        self._wake.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            self._collect_finished()
            self._claim_available_jobs()
            self._wake.wait(self.poll_interval)
            self._wake.clear()
        self._collect_finished()

    def _claim_available_jobs(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                executor = self._executor
                capacity = self.max_workers - len(self._futures)
            if executor is None or capacity <= 0:
                return
            job = job_store.claim_next_job()
            if job is None:
                return
            future = executor.submit(self._execute, job["job_id"])
            with self._lock:
                self._futures.add(future)

    def _collect_finished(self) -> None:
        with self._lock:
            completed = {future for future in self._futures if future.done()}
            self._futures.difference_update(completed)
        for future in completed:
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - _execute handles expected failures
                logger.exception(f"Unexpected analysis worker failure: {exc}")

    def _execute(self, job_id: str) -> None:
        handler = self._handler
        if handler is None:
            return
        started_at = time.monotonic()
        try:
            job_store.record_job_event(job_id, "job.started", status="running")
            handler(job_id)
        except Exception as exc:
            logger.exception(f"Queued analysis failed for {job_id}: {exc}")
            job_store.update_job(
                job_id,
                status="failed",
                error="Analisis gagal secara internal",
                message="Analisis gagal secara internal",
            )
        finally:
            elapsed_ms = int((time.monotonic() - started_at) * 1000)
            job = job_store.get_job(job_id)
            status = job.get("status") if job else "failed"
            job_store.record_job_event(
                job_id,
                "job.finished",
                status=status,
                duration_ms=elapsed_ms,
            )
            if job and status == "failed" and job.get("attempt", 0) < job.get("max_attempts", 2):
                delay = min(60, 2 ** max(0, int(job.get("attempt", 1)) - 1))
                retried = job_store.retry_job(job_id, delay_seconds=delay)
                if retried:
                    job_store.record_job_event(
                        job_id,
                        "job.retry_scheduled",
                        status="queued",
                        data={"delay_seconds": delay, "attempt": retried.get("attempt", 0)},
                    )
                    self.notify()


_queue: AnalysisJobQueue | None = None
_queue_lock = threading.Lock()


def get_analysis_queue() -> AnalysisJobQueue:
    """Return the process-local queue configured for the current deployment."""
    global _queue
    with _queue_lock:
        if _queue is None:
            config = get_config()
            queue_config = getattr(config, "queue", None)
            workers = int(getattr(queue_config, "max_workers", 2))
            _queue = AnalysisJobQueue(max_workers=workers)
        return _queue
