"""
Simple in-memory sliding-window rate limiter middleware.

Single-process implementation (sufficient for a single uvicorn instance).
Limits requests per client IP per minute based on ``api.rate_limit_*`` config.
Health checks, system stats, and read-only (GET) job-status polling are exempt
so monitoring dashboards never get throttled.
"""

import threading
import time
from collections import deque

from starlette.requests import Request
from starlette.responses import JSONResponse

EXEMPT_PATHS = {"/health", "/api/system-stats"}
# GET polling endpoints (status/events/artifacts/daftar job) — mutasi tetap dibatasi.
EXEMPT_GET_PREFIXES = ("/api/analysis-status/", "/api/analysis-jobs")


def _is_exempt(request: Request) -> bool:
    path = request.url.path
    if path in EXEMPT_PATHS:
        return True
    return request.method == "GET" and path.startswith(EXEMPT_GET_PREFIXES)


class SlidingWindowRateLimiter:
    """Per-IP sliding-window counter over a fixed window (seconds)."""

    def __init__(self, limit: int, window_seconds: float = 60.0):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            q = self._hits.setdefault(key, deque())
            cutoff = now - self.window
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


def create_rate_limit_middleware(limit: int, window_seconds: float = 60.0):
    """Build an HTTP middleware function enforcing the rate limit."""
    limiter = SlidingWindowRateLimiter(limit, window_seconds)

    async def rate_limit_middleware(request: Request, call_next):
        if _is_exempt(request):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        if not limiter.allow(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(int(window_seconds))},
            )
        return await call_next(request)

    rate_limit_middleware.limiter = limiter  # exposed for tests
    return rate_limit_middleware
