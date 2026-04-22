"""add stripe billing spine

Revision ID: 2a4d4d9f6b21
Revises: 0f5bf4901e6a
Create Date: 2026-04-22 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "2a4d4d9f6b21"
down_revision: Union[str, None] = "0f5bf4901e6a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("plan_status", sa.String(length=50), server_default="active", nullable=False),
        )
        batch_op.add_column(sa.Column("stripe_customer_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("stripe_price_id", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("stripe_price_lookup_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("billing_email", sa.String(length=320), nullable=True))
        batch_op.create_unique_constraint(
            "uq_organizations_stripe_customer_id",
            ["stripe_customer_id"],
        )
        batch_op.create_unique_constraint(
            "uq_organizations_stripe_subscription_id",
            ["stripe_subscription_id"],
        )

    op.create_table(
        "stripe_webhook_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("stripe_event_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=True),
        sa.Column("stripe_price_lookup_key", sa.String(length=255), nullable=True),
        sa.Column("billing_email", sa.String(length=320), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_event_id"),
    )


def downgrade() -> None:
    op.drop_table("stripe_webhook_events")
    with op.batch_alter_table("organizations", schema=None) as batch_op:
        batch_op.drop_constraint("uq_organizations_stripe_subscription_id", type_="unique")
        batch_op.drop_constraint("uq_organizations_stripe_customer_id", type_="unique")
        batch_op.drop_column("billing_email")
        batch_op.drop_column("current_period_end")
        batch_op.drop_column("stripe_price_lookup_key")
        batch_op.drop_column("stripe_price_id")
        batch_op.drop_column("stripe_subscription_id")
        batch_op.drop_column("stripe_customer_id")
        batch_op.drop_column("plan_status")
