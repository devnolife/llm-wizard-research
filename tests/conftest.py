"""
Pytest configuration
"""

import pytest
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture(autouse=True)
def setup_logging():
    """Setup logging for tests"""
    from loguru import logger
    logger.add("logs/test.log", rotation="10 MB")
