"""Tests for the sliding-window API rate limiter."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.utils.rate_limit import SlidingWindowRateLimiter, create_rate_limit_middleware


class TestSlidingWindowRateLimiter:
    def test_allows_up_to_limit(self):
        rl = SlidingWindowRateLimiter(limit=3)
        assert all(rl.allow("ip") for _ in range(3))
        assert rl.allow("ip") is False

    def test_keys_are_independent(self):
        rl = SlidingWindowRateLimiter(limit=1)
        assert rl.allow("a") is True
        assert rl.allow("a") is False
        assert rl.allow("b") is True

    def test_window_expiry(self, monkeypatch):
        import app.utils.rate_limit as mod
        t = [0.0]
        monkeypatch.setattr(mod.time, "monotonic", lambda: t[0])
        rl = SlidingWindowRateLimiter(limit=1, window_seconds=60)
        assert rl.allow("ip") is True
        assert rl.allow("ip") is False
        t[0] = 61.0
        assert rl.allow("ip") is True

    def test_reset(self):
        rl = SlidingWindowRateLimiter(limit=1)
        rl.allow("ip")
        rl.reset()
        assert rl.allow("ip") is True


@pytest.fixture()
def client():
    app = FastAPI()
    middleware = create_rate_limit_middleware(limit=2)

    @app.middleware("http")
    async def _mw(request, call_next):
        return await middleware(request, call_next)

    @app.get("/health")
    async def health():
        return {"ok": True}

    @app.get("/api/thing")
    async def thing():
        return {"ok": True}

    @app.get("/api/system-stats")
    async def system_stats():
        return {"ok": True}

    @app.get("/api/analysis-status/{job_id}/events")
    async def job_events(job_id: str):
        return {"ok": True}

    @app.post("/api/analysis-status/{job_id}/cancel")
    async def job_cancel(job_id: str):
        return {"ok": True}

    return TestClient(app)


class TestRateLimitMiddleware:
    def test_returns_429_after_limit(self, client):
        assert client.get("/api/thing").status_code == 200
        assert client.get("/api/thing").status_code == 200
        resp = client.get("/api/thing")
        assert resp.status_code == 429
        assert resp.headers.get("Retry-After") == "60"
        assert "Rate limit" in resp.json()["detail"]

    def test_health_exempt(self, client):
        for _ in range(10):
            assert client.get("/health").status_code == 200

    def test_monitoring_gets_exempt(self, client):
        for _ in range(10):
            assert client.get("/api/system-stats").status_code == 200
            assert client.get("/api/analysis-status/abc/events").status_code == 200

    def test_post_under_exempt_prefix_still_limited(self, client):
        assert client.post("/api/analysis-status/abc/cancel").status_code == 200
        assert client.post("/api/analysis-status/abc/cancel").status_code == 200
        assert client.post("/api/analysis-status/abc/cancel").status_code == 429
