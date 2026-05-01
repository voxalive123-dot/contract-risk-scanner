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
    assert "source_title" in columns
    assert "source_type" in columns
    assert "severity" in columns
    assert "top_findings_snapshot" in columns
    assert "clause_families_detected" in columns
    assert "synthesis_patterns_triggered" in columns
    assert "context_profile_snapshot" in columns
    assert "report_export_state" in columns
    assert "decision_intelligence_snapshot" in columns

    scan_note_columns = table_columns(DB_PATH, "scan_notes")
    assert "org_id" in scan_note_columns
    assert "scan_id" in scan_note_columns
    assert "finding_rule_id" in scan_note_columns
    assert "note" in scan_note_columns
    assert "created_by_user_id" in scan_note_columns

    policy_columns = table_columns(DB_PATH, "organization_risk_policies")
    assert "org_id" in policy_columns
    assert "policy_key" in policy_columns
    assert "policy_value" in policy_columns

    policy_audit_columns = table_columns(DB_PATH, "organization_risk_policy_audits")
    assert "old_value" in policy_audit_columns
    assert "new_value" in policy_audit_columns

    scan_decision_columns = table_columns(DB_PATH, "scan_decision_states")
    assert "state" in scan_decision_columns
    assert "reason_code" in scan_decision_columns

    finding_decision_columns = table_columns(DB_PATH, "finding_decision_statuses")
    assert "finding_id" in finding_decision_columns
    assert "status" in finding_decision_columns

    decision_note_columns = table_columns(DB_PATH, "decision_notes")
    assert "finding_id" in decision_note_columns
    assert "reason_code" in decision_note_columns

    decision_audit_columns = table_columns(DB_PATH, "decision_audit_logs")
    assert "previous_state" in decision_audit_columns
    assert "new_state" in decision_audit_columns

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

    internal_action_columns = table_columns(DB_PATH, "internal_operator_actions")
    assert "actor_user_id" in internal_action_columns
    assert "org_id" in internal_action_columns
    assert "action_type" in internal_action_columns
    assert "reason" in internal_action_columns
    assert "before_json" in internal_action_columns
    assert "after_json" in internal_action_columns

    owner_grant_columns = table_columns(DB_PATH, "owner_entitlement_grants")
    assert "org_id" in owner_grant_columns
    assert "user_id" in owner_grant_columns
    assert "granted_plan" in owner_grant_columns
    assert "grant_type" in owner_grant_columns
    assert "scan_quota_override" in owner_grant_columns
    assert "starts_at" in owner_grant_columns
    assert "expires_at" in owner_grant_columns
    assert "status" in owner_grant_columns
    assert "created_by_user_id" in owner_grant_columns
    assert "revoked_at" in owner_grant_columns

    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        cur.execute("SELECT version_num FROM alembic_version")
        row = cur.fetchone()
        assert row is not None
        assert row[0] == "e5f6a7b8c9d0"
    finally:
        conn.close()


def test_downgrade_then_upgrade_roundtrip() -> None:
    run_alembic("upgrade", "head")
    run_alembic("downgrade", "4f0598891ff7")

    columns_after_downgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" not in columns_after_downgrade
    assert "source_title" not in columns_after_downgrade
    assert "context_profile_snapshot" not in columns_after_downgrade
    assert "decision_intelligence_snapshot" not in columns_after_downgrade

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
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='internal_operator_actions'"
        )
        assert cur.fetchone() is None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='owner_entitlement_grants'"
        )
        assert cur.fetchone() is None
        cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='scan_notes'"
        )
        assert cur.fetchone() is None
        for table_name in (
            "organization_risk_policies",
            "organization_risk_policy_audits",
            "scan_decision_states",
            "finding_decision_statuses",
            "decision_notes",
            "decision_audit_logs",
        ):
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
            )
            assert cur.fetchone() is None
    finally:
        conn.close()

    run_alembic("upgrade", "head")

    columns_after_reupgrade = table_columns(DB_PATH, "scans")
    assert "scan_input_length" in columns_after_reupgrade
    assert "source_title" in columns_after_reupgrade
    assert "context_profile_snapshot" in columns_after_reupgrade
    assert "decision_intelligence_snapshot" in columns_after_reupgrade

    org_columns_after_reupgrade = table_columns(DB_PATH, "organizations")
    assert "plan_status" in org_columns_after_reupgrade

    subscription_columns_after_reupgrade = table_columns(DB_PATH, "subscriptions")
    assert "status" in subscription_columns_after_reupgrade

    internal_action_columns_after_reupgrade = table_columns(DB_PATH, "internal_operator_actions")
    assert "action_type" in internal_action_columns_after_reupgrade
    owner_grant_columns_after_reupgrade = table_columns(DB_PATH, "owner_entitlement_grants")
    assert "granted_plan" in owner_grant_columns_after_reupgrade
    scan_note_columns_after_reupgrade = table_columns(DB_PATH, "scan_notes")
    assert "scan_id" in scan_note_columns_after_reupgrade
    assert "policy_key" in table_columns(DB_PATH, "organization_risk_policies")
    assert "state" in table_columns(DB_PATH, "scan_decision_states")
    assert "status" in table_columns(DB_PATH, "finding_decision_statuses")
