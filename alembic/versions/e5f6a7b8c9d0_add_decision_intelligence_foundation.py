"""add decision intelligence foundation

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("decision_intelligence_snapshot", sa.Text(), nullable=True))

    op.create_table(
        "organization_risk_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("policy_key", sa.String(length=80), nullable=False),
        sa.Column("policy_value", sa.String(length=80), server_default="unknown", nullable=False),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "policy_key", name="uq_org_risk_policy_key"),
    )
    op.create_index("ix_org_risk_policies_org", "organization_risk_policies", ["org_id"])

    op.create_table(
        "organization_risk_policy_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("changed_by_user_id", sa.UUID(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("policy_key", sa.String(length=80), nullable=False),
        sa.Column("old_value", sa.String(length=80), nullable=True),
        sa.Column("new_value", sa.String(length=80), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_org_risk_policy_audits_org", "organization_risk_policy_audits", ["org_id"])

    op.create_table(
        "scan_decision_states",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("state", sa.String(length=50), server_default="pending", nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "scan_id", name="uq_scan_decision_org_scan"),
    )
    op.create_index("ix_scan_decision_states_org_scan", "scan_decision_states", ["org_id", "scan_id"])

    op.create_table(
        "finding_decision_statuses",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="unresolved", nullable=False),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id", "scan_id", "finding_id", name="uq_finding_decision_org_scan_finding"),
    )
    op.create_index("ix_finding_decision_statuses_org_scan", "finding_decision_statuses", ["org_id", "scan_id"])

    op.create_table(
        "decision_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.String(length=120), nullable=True),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_notes_org_scan", "decision_notes", ["org_id", "scan_id"])

    op.create_table(
        "decision_audit_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("finding_id", sa.String(length=120), nullable=True),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("previous_state", sa.String(length=80), nullable=True),
        sa.Column("new_state", sa.String(length=80), nullable=True),
        sa.Column("reason_code", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_decision_audit_logs_org_scan", "decision_audit_logs", ["org_id", "scan_id"])


def downgrade() -> None:
    op.drop_index("ix_decision_audit_logs_org_scan", table_name="decision_audit_logs")
    op.drop_table("decision_audit_logs")
    op.drop_index("ix_decision_notes_org_scan", table_name="decision_notes")
    op.drop_table("decision_notes")
    op.drop_index("ix_finding_decision_statuses_org_scan", table_name="finding_decision_statuses")
    op.drop_table("finding_decision_statuses")
    op.drop_index("ix_scan_decision_states_org_scan", table_name="scan_decision_states")
    op.drop_table("scan_decision_states")
    op.drop_index("ix_org_risk_policy_audits_org", table_name="organization_risk_policy_audits")
    op.drop_table("organization_risk_policy_audits")
    op.drop_index("ix_org_risk_policies_org", table_name="organization_risk_policies")
    op.drop_table("organization_risk_policies")
    op.drop_column("scans", "decision_intelligence_snapshot")
