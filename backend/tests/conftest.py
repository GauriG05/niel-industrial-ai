"""Pytest configuration and environment isolation."""

import os
from pathlib import Path
import pytest

# Ensure tests run strictly in test environment to avoid modifying production data
os.environ["ENVIRONMENT"] = "test"

from backend.app.config import get_settings


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    settings = get_settings()
    test_index_dir = settings.DATA_DIR / "test_index"
    test_index_dir.mkdir(parents=True, exist_ok=True)
    yield
    # Cleanup test index files after test session
    for f in test_index_dir.glob("*"):
        try:
            f.unlink()
        except Exception:
            pass

