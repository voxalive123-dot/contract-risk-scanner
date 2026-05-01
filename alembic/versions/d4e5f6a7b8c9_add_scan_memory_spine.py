"""add scan memory spine

Revision ID: d4e5f6a7b8c9
Revises: c3f4e5a6b7d8
Create Date: 2026-05-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3f4e5a6b7d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scans", sa.Column("source_title", sa.String(length=255), nullable=True))
    op.add_column("scans", sa.Column("source_type", sa.String(length=50), server_default="unknown", nullable=False))
    op.add_column("scans", sa.Column("severity", sa.String(length=20), nullable=True))
    op.add_column("scans", sa.Column("top_findings_snapshot", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("clause_families_detected", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("synthesis_patterns_triggered", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("context_profile_snapshot", sa.Text(), nullable=True))
    op.add_column("scans", sa.Column("report_export_state", sa.String(length=50), server_default="absent", nullable=False))

    op.create_table(
        "scan_notes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("scan_id", sa.UUID(), nullable=False),
        sa.Column("finding_rule_id", sa.String(length=120), nullable=True),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_by_user_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scan_notes_org_scan", "scan_notes", ["org_id", "scan_id"])


def downgrade() -> None:
    op.drop_index("ix_scan_notes_org_scan", table_name="scan_notes")
    op.drop_table("scan_notes")
    op.drop_column("scans", "report_export_state")
    op.drop_column("scans", "context_profile_snapshot")
    op.drop_column("scans", "synthesis_patterns_triggered")
    op.drop_column("scans", "clause_families_detected")
    op.drop_column("scans", "top_findings_snapshot")
    op.drop_column("scans", "severity")
    op.drop_column("scans", "source_type")
    op.drop_column("scans", "source_title")
