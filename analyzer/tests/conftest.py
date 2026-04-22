import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text


ROOT = Path(__file__).resolve().parents[2]
TEST_DB_PATH = ROOT / "test_suite.db"
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("TEST_API_KEY", "vxrk_local_dev_fallback_key")

if TEST_DB_PATH.exists():
    TEST_DB_PATH.unlink(missing_ok=True)

subprocess.run(
    [sys.executable, "init_db.py"],
    cwd=ROOT,
    env=os.environ.copy(),
    capture_output=True,
    text=True,
    check=True,
)
subprocess.run(
    [sys.executable, "seed_api_key.py"],
    cwd=ROOT,
    env=os.environ.copy(),
    capture_output=True,
    text=True,
    check=True,
)

from main import app
import api
from db import engine


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    yield
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def reset_shared_test_state():
    api._BUCKETS.clear()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM usage_logs"))
        conn.execute(text("DELETE FROM scans"))
    yield
    api._BUCKETS.clear()


@pytest.fixture
def client():
    return TestClient(app)
