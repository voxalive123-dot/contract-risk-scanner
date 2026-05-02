"""add account dashboards

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-05-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("account_status", sa.String(length=50), server_default="active", nullable=False))
    op.add_column("users", sa.Column("closure_requested_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("soft_deleted_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "account_profiles",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=False),
        sa.Column("legal_first_name", sa.String(length=120), nullable=True),
        sa.Column("legal_last_name", sa.String(length=120), nullable=True),
        sa.Column("business_company_name", sa.String(length=255), nullable=True),
        sa.Column("role_title", sa.String(length=160), nullable=True),
        sa.Column("country", sa.String(length=120), nullable=True),
        sa.Column("business_email", sa.String(length=320), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("business_category", sa.String(length=160), nullable=True),
        sa.Column("display_name", sa.String(length=160), nullable=True),
        sa.Column("workspace_name", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_account_profiles_user_id"),
    )

    op.create_table(
        "billing_invoices",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("provider", sa.String(length=50), server_default="stripe", nullable=False),
        sa.Column("external_invoice_id", sa.String(length=255), nullable=False),
        sa.Column("external_customer_id", sa.String(length=255), nullable=True),
        sa.Column("external_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), server_default="unknown", nullable=False),
        sa.Column("amount_due", sa.Integer(), nullable=True),
        sa.Column("amount_paid", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("hosted_invoice_url", sa.Text(), nullable=True),
        sa.Column("invoice_pdf", sa.Text(), nullable=True),
        sa.Column("invoice_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "external_invoice_id", name="uq_billing_invoice_provider_external"),
    )


def downgrade() -> None:
    op.drop_table("billing_invoices")
    op.drop_table("account_profiles")
    op.drop_column("users", "soft_deleted_at")
    op.drop_column("users", "disabled_at")
    op.drop_column("users", "closure_requested_at")
    op.drop_column("users", "account_status")
