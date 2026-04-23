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

    org_columns = table_columns(DB_PATH, "organizations")
    assert "plan_status" in org_columns
    assert "stripe_customer_id" in org_columns
    assert "stripe_subscription_id" in org_columns
    assert "stripe_price_lookup_key" in org_columns
    assert "current_period_end" in org_columns
    assert "billing_email" in org_columns

    stripe_event_columns = table_columns(DB_PATH, "stripe_webhook_events")
    assert "stripe_event_id" in stripe_event_columns
    assert "processing_status" in stripe_event_columns
    assert "org_id" in stripe_event_columns

    membership_columns = table_columns(DB_PATH, "memberships")
    assert "user_id" in membership_columns
    assert "org_id" in membership_columns
    assert "status" in membership_columns

    account_token_columns = table_columns(DB_PATH, "account_password_tokens")
    assert "user_id" in account_token_columns
    assert "token_hash" in account_token_columns
    assert "purpose" in account_token_columns
    assert "expires_at" in account_token_columns
    assert "used_at" in account_token_columns

    org_invite_columns = table_columns(DB_PATH, "organization_invites")
    assert "org_id" in org_invite_columns
    assert "invited_email" in org_invite_columns
    assert "role" in org_invite_columns
    assert "token_hash" in org_invite_columns
    assert "status" in org_invite_columns
    assert "accepted_at" in org_invite_columns

    billing_customer_columns = table_columns(DB_PATH, "billing_customer_references")
    assert "external_customer_id" in billing_customer_columns
    assert "org_id" in billing_customer_columns

    subscription_columns = table_columns(DB_PATH, "subscriptions")
    assert "plan_name" in subscription_columns
    assert "status" in subscription_columns
    assert "is_current" in subscription_columns

    ai_usage_columns = table_columns(DB_PATH, "ai_usage_meters")
    assert "usage_count" in ai_usage_columns
    assert "period_start" in ai_usage_columns

    monitoring_columns = table_columns(DB_PATH, "monitoring_signals")
    assert "signal_type" in monitoring_columns
    assert "severity" in monitoring_columns

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "9c1f0d2a8b7e"
    finally:
        conn.close()


def test_downgrade_then_upgrade_roundtrip() -> None:
    run_alembic("upgrade", "head")
    run_alembic("downgrade", "4f0598891ff7")

    columns_after_downgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" not in columns_after_downgrade

    org_columns_after_downgrade = table_columns(DB_PATH, "organizations")
    assert "plan_status" not in org_columns_after_downgrade

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='stripe_webhook_events'"
        )
        assert cur.fetchone() is None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='subscriptions'"
        )
        assert cur.fetchone() is None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='account_password_tokens'"
        )
        assert cur.fetchone() is None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='organization_invites'"
        )
        assert cur.fetchone() is None
    finally:
        conn.close()

    run_alembic("upgrade", "head")

    columns_after_reupgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" in columns_after_reupgrade

    org_columns_after_reupgrade = table_columns(DB_PATH, "organizations")
    assert "plan_status" in org_columns_after_reupgrade

    subscription_columns_after_reupgrade = table_columns(DB_PATH, "subscriptions")
    assert "status" in subscription_columns_after_reupgrade
