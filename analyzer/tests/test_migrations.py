import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = ROOT / "alembic.ini"
DB_PATH = ROOT / "test_migrations.db"
DB_URL = f"sqlite:///{DB_PATH}"


def run_alembic(*args: str) -> subprocess.CompletedProcess:
    env = dict(**__import__("os").environ)
    env["DATABASE_URL"] = DB_URL
    return subprocess.run(
        [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )


def table_columns(db_path: Path, table_name: str) -> list[str]:
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute(f"PRAGMA table_info({table_name});")
        return [row[1] for row in cur.fetchall()]
    finally:
        conn.close()


def setup_function() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()


def teardown_function() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()


def test_upgrade_head_on_fresh_db() -> None:
    run_alembic("upgrade", "head")

    assert DB_PATH.exists()

    columns = table_columns(DB_PATH, "scans")
    assert "scan_input_length" in columns

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "0f5bf4901e6a"
    finally:
        conn.close()


def test_downgrade_then_upgrade_roundtrip() -> None:
    run_alembic("upgrade", "head")
    run_alembic("downgrade", "4f0598891ff7")

    columns_after_downgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" not in columns_after_downgrade

    run_alembic("upgrade", "head")

    columns_after_reupgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" in columns_after_reupgrade
