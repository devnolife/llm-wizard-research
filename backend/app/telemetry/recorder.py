"""Privacy-preserving runtime telemetry.

Events deliberately hold operational metadata only.  Content-bearing values
such as prompts, queries, PDF text, and chat messages never enter this module.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Awaitable, Callable

from fastapi import Request, Response
from loguru import logger

from ..utils import job_store
from ..utils.config_loader import get_config


async def telemetry_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Attach a request ID and log only method/path/status/duration metadata."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    started_at = time.monotonic()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = int((time.monotonic() - started_at) * 1000)
        logger.error(
            "request_failed request_id={} method={} path={} duration_ms={}",
            request_id,
            request.method,
            request.url.path,
            duration_ms,
        )
        raise
    duration_ms = int((time.monotonic() - started_at) * 1000)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed request_id={} method={} path={} status={} duration_ms={}",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


def record_job_event(
    job_id: str,
    event_type: str,
    *,
    phase: str | None = None,
    status: str | None = None,
    duration_ms: int | None = None,
    data: dict[str, Any] | None = None,
) -> None:
    """Write an event only when metadata telemetry is enabled."""
    if not getattr(get_config().telemetry, "enabled", True):
        return
    job_store.record_job_event(
        job_id,
        event_type,
        phase=phase,
        status=status,
        duration_ms=duration_ms,
        data=data,
    )
