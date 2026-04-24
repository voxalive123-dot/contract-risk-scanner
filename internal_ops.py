from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from account_auth import AccountContext
from crud import month_start_utc
from entitlement_diagnostics import build_entitlement_diagnostics
from entitlement_spine import resolve_entitlement_for_org
from models import (
    AIUsageMeter,
    BillingCustomerReference,
    InternalOperatorAction,
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


def _sum(db: Session, selectable) -> int:
    value = db.execute(selectable).scalar_one()
    return int(value or 0)


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


def _account_snapshot(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
        "is_active": user.is_active,
        "org_id": str(user.org_id),
        "created_at": _serialize_dt(user.created_at),
    }


def _operator_action_snapshot(action: InternalOperatorAction) -> dict[str, Any]:
    return {
        "id": str(action.id),
        "actor_user_id": str(action.actor_user_id),
        "org_id": str(action.org_id) if action.org_id else None,
        "target_type": action.target_type,
        "target_id": action.target_id,
        "action_type": action.action_type,
        "reason": action.reason,
        "before": action.before_json,
        "after": action.after_json,
        "created_at": _serialize_dt(action.created_at),
    }


def _current_month_scan_count(db: Session, *, org_id: uuid.UUID | None = None) -> int:
    month_start = month_start_utc()
    stmt = select(func.count()).select_from(Scan).where(Scan.created_at >= month_start)
    if org_id is not None:
        stmt = stmt.where(Scan.org_id == org_id)
    return int(db.execute(stmt).scalar_one())


def _recent_usage_logs(
    db: Session,
    *,
    status_code: int | None = None,
    status_code_min: int | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    stmt = select(UsageLog).order_by(UsageLog.created_at.desc()).limit(limit)
    if status_code is not None:
        stmt = (
            select(UsageLog)
            .where(UsageLog.status_code == status_code)
            .order_by(UsageLog.created_at.desc())
            .limit(limit)
        )
    elif status_code_min is not None:
        stmt = (
            select(UsageLog)
            .where(UsageLog.status_code >= status_code_min)
            .order_by(UsageLog.created_at.desc())
            .limit(limit)
        )
    return [_usage_log_snapshot(log) for log in db.execute(stmt).scalars().all()]


def _recent_operator_actions(db: Session, *, org_id: uuid.UUID | None = None, limit: int = 10) -> list[dict[str, Any]]:
    stmt = select(InternalOperatorAction).order_by(InternalOperatorAction.created_at.desc()).limit(limit)
    if org_id is not None:
        stmt = (
            select(InternalOperatorAction)
            .where(InternalOperatorAction.org_id == org_id)
            .order_by(InternalOperatorAction.created_at.desc())
            .limit(limit)
        )
    return [_operator_action_snapshot(action) for action in db.execute(stmt).scalars().all()]


def _status_badge(entitlement: dict[str, Any]) -> dict[str, str]:
    if entitlement["subscription_state"] == "restricted" or entitlement["fail_closed"]:
        return {"label": "Restricted", "tone": "danger"}
    if entitlement["paid_access"]:
        return {"label": entitlement["effective_plan"].title(), "tone": "success"}
    return {"label": "Starter", "tone": "neutral"}


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
    month_start = month_start_utc()
    orgs = list(
        db.execute(
            select(Organization).order_by(Organization.created_at.desc()).limit(limit)
        ).scalars().all()
    )
    overview = {
        "total_organizations": len(orgs),
        "total_accounts": _count(db, User),
        "total_memberships": _count(db, Membership),
        "active_organizations": 0,
        "restricted_organizations": 0,
        "legacy_plan_type_counts": {},
        "effective_plan_counts": {},
        "scans_this_month": _current_month_scan_count(db),
        "quota_blocked_requests_this_month": _count(
            db,
            UsageLog,
            UsageLog.created_at >= month_start,
            UsageLog.status_code == 429,
        ),
        "recent_quota_blocked_requests": _recent_usage_logs(db, status_code=429, limit=10),
        "error_operations_this_month": _count(
            db,
            UsageLog,
            UsageLog.created_at >= month_start,
            UsageLog.status_code >= 500,
        ),
        "recent_error_operations": _recent_usage_logs(db, status_code_min=500, limit=10),
        "ai_usage_this_month": _sum(
            db,
            select(func.coalesce(func.sum(AIUsageMeter.usage_count), 0)).where(AIUsageMeter.period_start >= month_start),
        ),
    }
    summaries: list[dict[str, Any]] = []
    for org in orgs:
        entitlement = resolve_entitlement_for_org(db, org)
        entitlement_dict = asdict(entitlement)
        subscription = _current_subscription(db, org.id)
        reference = _billing_reference(db, org.id)
        platform_context = _platform_context(db, org)
        monthly_scans_used = _current_month_scan_count(db, org_id=org.id)
        account_count = _count(db, User, User.org_id == org.id)
        overview["legacy_plan_type_counts"][org.plan_type] = overview["legacy_plan_type_counts"].get(org.plan_type, 0) + 1
        overview["effective_plan_counts"][entitlement.effective_plan] = overview["effective_plan_counts"].get(entitlement.effective_plan, 0) + 1
        if entitlement.fail_closed or entitlement.subscription_state == "restricted":
            overview["restricted_organizations"] += 1
        else:
            overview["active_organizations"] += 1
        summaries.append(
            {
                "id": str(org.id),
                "name": org.name,
                "created_at": _serialize_dt(org.created_at),
                "legacy_plan_type": org.plan_type,
                "legacy_plan_status": org.plan_status,
                "plan_limit": org.plan_limit,
                "stripe_customer_id": org.stripe_customer_id,
                "stripe_subscription_id": org.stripe_subscription_id,
                "effective_entitlement": entitlement_dict,
                "subscription": {
                    "plan_name": subscription.plan_name,
                    "status": subscription.status,
                    "source": subscription.source,
                    "external_subscription_id": subscription.external_subscription_id,
                    "external_customer_id": subscription.external_customer_id,
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
                "account_count": account_count,
                "member_count": _count(db, Membership, Membership.org_id == org.id),
                "pending_invite_count": _count(
                    db,
                    OrganizationInvite,
                    OrganizationInvite.org_id == org.id,
                    OrganizationInvite.status == "pending",
                ),
                "scan_count": _count(db, Scan, Scan.org_id == org.id),
                "monthly_scans_used": monthly_scans_used,
                "status_badge": _status_badge(entitlement_dict),
                "platform_context": platform_context,
            }
        )
    return {
        "read_only": True,
        "overview": overview,
        "recent_operator_actions": _recent_operator_actions(db, limit=20),
        "organizations": summaries,
    }


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
    users = list(
        db.execute(
            select(User).where(User.org_id == org.id).order_by(User.created_at.asc())
        ).scalars().all()
    )
    subscription = _current_subscription(db, org.id)
    reference = _billing_reference(db, org.id)
    entitlement = resolve_entitlement_for_org(db, org)

    return {
        "found": True,
        "read_only": True,
        "organization": {
            "id": str(org.id),
            "name": org.name,
            "plan_type": org.plan_type,
            "plan_status": org.plan_status,
            "plan_limit": org.plan_limit,
            "stripe_customer_id": org.stripe_customer_id,
            "stripe_subscription_id": org.stripe_subscription_id,
            "stripe_price_id": org.stripe_price_id,
            "stripe_price_lookup_key": org.stripe_price_lookup_key,
            "billing_email": org.billing_email,
            "current_period_end": _serialize_dt(org.current_period_end),
            "created_at": _serialize_dt(org.created_at),
        },
        "platform_context": _platform_context(db, org),
        "current_subscription": {
            "plan_name": subscription.plan_name,
            "status": subscription.status,
            "source": subscription.source,
            "external_subscription_id": subscription.external_subscription_id,
            "external_customer_id": subscription.external_customer_id,
            "current_period_end": _serialize_dt(subscription.current_period_end),
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
        "effective_entitlement": asdict(entitlement),
        "diagnostics": build_entitlement_diagnostics(db, org_id=org.id, webhook_limit=5),
        "accounts": [_account_snapshot(user) for user in users],
        "memberships": [_membership_snapshot(db, membership) for membership in memberships],
        "recent_invites": [_invite_snapshot(invite) for invite in invites],
        "recent_scans": [_recent_scan_snapshot(scan) for scan in scans],
        "recent_usage": [_usage_log_snapshot(log) for log in usage],
        "recent_operator_actions": _recent_operator_actions(db, org_id=org.id, limit=20),
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
        "manual_controls": [
            "operator_note",
            "cancel_pending_invite",
            "restrict_organization",
            "reactivate_organization",
            "manual_override_organization",
            "downgrade_organization_to_starter",
        ],
    }
