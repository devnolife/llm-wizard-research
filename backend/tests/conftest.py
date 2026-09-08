"""Shared pytest configuration for the installed backend package."""

import os
from pathlib import Path

import pytest
from loguru import logger

# Disable API rate limiting during tests (full suite exceeds the per-minute
# quota); the limiter itself is covered by tests/test_rate_limit.py.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Use one bounded test log sink instead of adding one per test case."""
    Path("logs").mkdir(exist_ok=True)
    # retention: tanpa ini setiap rotasi menyisakan test.<timestamp>.log selamanya
    sink_id = logger.add("logs/test.log", rotation="10 MB", retention=3, level="WARNING")
    yield
    logger.remove(sink_id)


@pytest.fixture(autouse=True)
def _openalex_check_enabled_by_default(monkeypatch):
    """Netralkan saklar OPENALEX_DISABLED dari backend/.env pengembang.

    ``ConfigLoader()`` memanggil ``load_dotenv(override=True)`` kapan pun ia
    dibuat, sehingga nilai ``.env`` bocor ke tes berikutnya dan tes perilaku cek
    kebaruan (yang memakai klien OpenAlex palsu) ikut berubah. Tes yang sengaja
    menguji saklar menyetelnya sendiri lewat ``monkeypatch.setenv``.
    """
    monkeypatch.setenv("OPENALEX_DISABLED", "0")
