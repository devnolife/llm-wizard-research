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
    sink_id = logger.add("logs/test.log", rotation="10 MB", level="WARNING")
    yield
    logger.remove(sink_id)
