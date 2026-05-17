"""add context intelligence spine

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-05-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONTEXT_COLUMNS = (
    ("context_user_role", sa.String(length=50)),
    ("context_contract_type", sa.String(length=80)),
    ("context_criticality_level", sa.String(length=50)),
    ("context_risk_posture", sa.String(length=50)),
    ("context_deal_value", sa.String(length=80)),
    ("context_industry", sa.String(length=120)),
    ("context_jurisdiction", sa.String(length=80)),
    ("context_negotiation_leverage", sa.String(length=50)),
    ("context_counterparty_tier", sa.String(length=80)),
    ("context_data_sensitivity", sa.String(length=80)),
    ("context_insurance_coverage", sa.String(length=80)),
    ("context_capture_version", sa.String(length=50)),
)


def upgrade() -> None:
    for name, column_type in CONTEXT_COLUMNS:
        op.add_column("scans", sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    for name, _column_type in reversed(CONTEXT_COLUMNS):
        op.drop_column("scans", name)
