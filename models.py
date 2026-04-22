# models.py
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Column,
    func,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from db import Base

# ---------------------------
# Organizations
# ---------------------------
class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

# ADD THIS LINE
    plan_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("plans.id"),
        nullable=True,
    )

    # Your screenshots prove this exists and is NOT NULL.
    plan_limit: Mapped[int] = mapped_column(Integer, nullable=False)

    # Your failed insert row showed "starter" being present, meaning a tier/plan column exists with default.
    # In your DB it is NOT named "plan" (you got: column "plan" does not exist).
    # Common name used in our build: plan_tier
    plan_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="starter")

    plan_status: Mapped[str] = mapped_column(String(50), nullable=False, server_default="active")

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_lookup_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    current_period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    users: Mapped[List["User"]] = relationship("User", back_populates="organization")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="organization")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="organization")
    usage_logs: Mapped[List["UsageLog"]] = relationship("UsageLog", back_populates="organization")

    plan: Mapped[Optional["Plan"]] = relationship("Plan")

# ---------------------------
# Users
# ---------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Matches your `\d users` output:
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False, server_default="owner")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user")
    scans: Mapped[List["Scan"]] = relationship("Scan", back_populates="user")
    usage_logs: Mapped[List["UsageLog"]] = relationship("UsageLog", back_populates="user")


# ---------------------------
# API Keys
# ---------------------------
class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    # EXEC-GRADE FIX: this must exist because your code expects api_key.user_id
    # and you already added the column in Postgres.
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Matches your `\d api_keys` output:
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="api_keys")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="api_keys")
    usage_logs: Mapped[List["UsageLog"]] = relationship("UsageLog", back_populates="api_key")


# ---------------------------
# Scans (used by /analyze persistence)
# ---------------------------
class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    request_id: Mapped[str] = mapped_column(String(128), nullable=False)

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_density: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[int] = mapped_column(Integer, nullable=False)

    ruleset_version: Mapped[str] = mapped_column(String(50), nullable=False)

    scan_input_length: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="scans")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="scans")


# ---------------------------
# Usage Logs (used by /analyze usage logging)
# ---------------------------
class UsageLog(Base):
    __tablename__ = "usage_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    org_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    api_key_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
    )

    endpoint: Mapped[str] = mapped_column(String(100), nullable=False, server_default="/analyze")
    method: Mapped[str] = mapped_column(String(10), nullable=False, server_default="POST")

    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    request_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    ip: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="usage_logs")
    user: Mapped[Optional["User"]] = relationship("User", back_populates="usage_logs")
    api_key: Mapped[Optional["ApiKey"]] = relationship("ApiKey", back_populates="usage_logs")

class Plan(Base):
    __tablename__ = "plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String, unique=True, nullable=False)

    monthly_scan_quota = Column(Integer, nullable=False)

    burst_limit = Column(Integer, nullable=False)

    sustained_limit = Column(Integer, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class StripeWebhookEvent(Base):
    __tablename__ = "stripe_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    stripe_event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    processing_status: Mapped[str] = mapped_column(String(50), nullable=False)

    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,
    )

    stripe_customer_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    stripe_price_lookup_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
