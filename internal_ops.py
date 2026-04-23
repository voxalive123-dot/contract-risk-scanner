from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import AccountContext
from entitlement_diagnostics import build_entitlement_diagnostics
from entitlement_spine import resolve_entitlement_for_org
from models import (
    BillingCustomerReference,
    Membership,
    MonitoringSignal,
    Organization,
    OrganizationInvite,
    Scan,
    StripeWebhookEvent,
    Subscription,
    UsageLog,
    User,
)
from platform_owner import (
    choose_canonical_platform_org,
    is_platform_like_org_name,
    platform_owner_membership_statuses,
)


class InternalOpsError(Exception):
    pass


class InternalOpsConfigError(InternalOpsError):
    pass


class InternalOpsForbiddenError(InternalOpsError):
    pass


def _serialize_dt(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def platform_owner_email() -> str | None:
    raw = os.getenv("PLATFORM_OWNER_EMAIL", "").strip().lower()
    return raw or None


def internal_admin_emails() -> set[str]:
    raw = os.getenv("INTERNAL_ADMIN_EMAILS", "")
    emails = {item.strip().lower() for item in raw.split(",") if item.strip()}
    owner_email = platform_owner_email()
    if owner_email:
        emails.add(owner_email)
    return emails


def require_internal_admin(context: AccountContext) -> None:
    allowed = internal_admin_emails()
    if not allowed:
        raise InternalOpsConfigError("Internal operations access is not configured")
    if context.user.email.strip().lower() not in allowed:
        raise InternalOpsForbiddenError("Account is not an internal platform admin")


def _current_subscription(db: Session, org_id: uuid.UUID) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org_id, Subscription.is_current.is_(True))
        .order_by(Subscription.updated_at.desc(), Subscription.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _billing_reference(db: Session, org_id: uuid.UUID) -> BillingCustomerReference | None:
    stmt = select(BillingCustomerReference).where(BillingCustomerReference.org_id == org_id).limit(1)
    return db.execute(stmt).scalars().first()


def _count(db: Session, model, *criteria) -> int:
    stmt = select(func.count()).select_from(model)
    for item in criteria:
        stmt = stmt.where(item)
    return int(db.execute(stmt).scalar_one())


def _recent_scan_snapshot(scan: Scan) -> dict[str, Any]:
    return {
        "id": str(scan.id),
        "request_id": scan.request_id,
        "risk_score": scan.risk_score,
        "risk_density": scan.risk_density,
        "confidence": scan.confidence,
        "ruleset_version": scan.ruleset_version,
        "created_at": _serialize_dt(scan.created_at),
    }


def _usage_log_snapshot(log: UsageLog) -> dict[str, Any]:
    return {
        "id": str(log.id),
        "endpoint": log.endpoint,
        "method": log.method,
        "status_code": log.status_code,
        "request_id": log.request_id,
        "created_at": _serialize_dt(log.created_at),
    }


def _signal_snapshot(signal: MonitoringSignal) -> dict[str, Any]:
    return {
        "id": str(signal.id),
        "category": signal.category,
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "message": signal.message,
        "created_at": _serialize_dt(signal.created_at),
    }


def _invite_snapshot(invite: OrganizationInvite) -> dict[str, Any]:
    return {
        "id": str(invite.id),
        "email": invite.invited_email,
        "role": invite.role,
        "status": invite.status,
        "expires_at": _serialize_dt(invite.expires_at),
        "accepted_at": _serialize_dt(invite.accepted_at),
        "created_at": _serialize_dt(invite.created_at),
    }


def _membership_snapshot(db: Session, membership: Membership) -> dict[str, Any]:
    user = db.get(User, membership.user_id)
    return {
        "id": str(membership.id),
        "user_id": str(membership.user_id),
        "email": user.email if user else None,
        "role": membership.role,
        "status": membership.status,
        "created_at": _serialize_dt(membership.created_at),
    }


def _platform_context(db: Session, org: Organization) -> dict[str, Any] | None:
    canonical_org, reason = choose_canonical_platform_org(db)
    if canonical_org is None:
        return None

    owner_statuses = platform_owner_membership_statuses(db, org=org)
    is_platform_org = is_platform_like_org_name(org.name) or bool(owner_statuses) or org.id == canonical_org.id
    if not is_platform_org:
        return None

    status = "canonical_platform_org" if org.id == canonical_org.id else "legacy_platform_org"
    return {
        "status": status,
        "reason": reason,
        "canonical_org_id": str(canonical_org.id),
        "canonical_org_name": canonical_org.name,
        "owner_memberships": owner_statuses,
    }


def list_internal_organizations(db: Session, *, limit: int = 100) -> dict[str, Any]:
    orgs = list(
        db.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(limit)
        ).scalars().all()
    )
    summaries: list[dict[str, Any]] = []
    for org in orgs:
        entitlement = resolve_entitlement_for_org(db, org)
        subscription = _current_subscription(db, org.id)
        reference = _billing_reference(db, org.id)
        platform_context = _platform_context(db, org)
        summaries.append(
            {
                "id": str(org.id),
                "name": org.name,
                "created_at": _serialize_dt(org.created_at),
                "legacy_plan_type": org.plan_type,
                "legacy_plan_status": org.plan_status,
                "effective_entitlement": asdict(entitlement),
                "subscription": {
                    "plan_name": subscription.plan_name,
                    "status": subscription.status,
                    "source": subscription.source,
                }
                if subscription
                else None,
                "billing_customer_reference": {
                    "provider": reference.provider,
                    "external_customer_id": reference.external_customer_id,
                    "billing_email": reference.billing_email,
                }
                if reference
                else None,
                "member_count": _count(db, Membership, Membership.org_id == org.id),
                "pending_invite_count": _count(
                    db,
                    OrganizationInvite,
                    OrganizationInvite.org_id == org.id,
                    OrganizationInvite.status == "pending",
                ),
                "scan_count": _count(db, Scan, Scan.org_id == org.id),
                "platform_context": platform_context,
            }
        )
    return {"read_only": True, "organizations": summaries}


def get_internal_organization_detail(db: Session, *, org_id: uuid.UUID | str) -> dict[str, Any]:
    parsed = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
    org = db.get(Organization, parsed)
    if org is None:
        return {"found": False, "org_id": str(parsed), "read_only": True}

    memberships = list(
        db.execute(
            select(Membership).where(Membership.org_id == org.id).order_by(Membership.created_at.asc())
        ).scalars().all()
    )
    invites = list(
        db.execute(
            select(OrganizationInvite).where(OrganizationInvite.org_id == org.id).order_by(OrganizationInvite.created_at.desc()).limit(20)
        ).scalars().all()
    )
    scans = list(
        db.execute(
            select(Scan).where(Scan.org_id == org.id).order_by(Scan.created_at.desc()).limit(10)
        ).scalars().all()
    )
    usage = list(
        db.execute(
            select(UsageLog).where(UsageLog.org_id == org.id).order_by(UsageLog.created_at.desc()).limit(10)
        ).scalars().all()
    )
    signals = list(
        db.execute(
            select(MonitoringSignal).where(MonitoringSignal.org_id == org.id).order_by(MonitoringSignal.created_at.desc()).limit(10)
        ).scalars().all()
    )
    webhooks = list(
        db.execute(
            select(StripeWebhookEvent).where(StripeWebhookEvent.org_id == org.id).order_by(StripeWebhookEvent.processed_at.desc()).limit(10)
        ).scalars().all()
    )

    return {
        "found": True,
        "read_only": True,
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "created_at": _serialize_dt(org.created_at),
        },
        "platform_context": _platform_context(db, org),
        "diagnostics": build_entitlement_diagnostics(db, org_id=org.id, webhook_limit=5),
        "memberships": [_membership_snapshot(db, membership) for membership in memberships],
        "recent_invites": [_invite_snapshot(invite) for invite in invites],
        "recent_scans": [_recent_scan_snapshot(scan) for scan in scans],
        "recent_usage": [_usage_log_snapshot(log) for log in usage],
        "recent_signals": [_signal_snapshot(signal) for signal in signals],
        "recent_webhooks": [
            {
                "id": str(event.id),
                "stripe_event_id": event.stripe_event_id,
                "event_type": event.event_type,
                "processing_status": event.processing_status,
                "error": event.error,
                "processed_at": _serialize_dt(event.processed_at),
            }
            for event in webhooks
        ],
        "manual_controls": [],
    }
