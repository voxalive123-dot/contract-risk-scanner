from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Organization, Subscription
from stripe_billing import DEFAULT_PLAN_LIMIT, DEFAULT_PLAN_NAME, PLAN_QUOTAS


PAID_PLAN_NAMES = {"business", "executive", "enterprise"}
SUBSCRIPTION_STATES = {
    "no_subscription",
    "checkout_started",
    "active",
    "trialing",
    "past_due",
    "unpaid",
    "canceled",
    "incomplete",
    "incomplete_expired",
    "restricted",
    "manual_override",
}
ENTITLEMENT_GRANTING_STATES = {"active", "trialing", "manual_override"}
ORGANIZATION_OVERRIDE_STATES = {"restricted", "manual_override"}


@dataclass(frozen=True)
class EntitlementResolution:
    organization_id: str | None
    source: str
    subscription_state: str
    raw_subscription_state: str | None
    plan_name: str
    effective_plan: str
    monthly_scan_limit: int
    paid_access: bool
    ai_review_notes_allowed: bool
    fail_closed: bool
    reason: str


def _normalize(value: str | None, fallback: str) -> str:
    if not value:
        return fallback
    normalized = value.strip().lower()
    return normalized or fallback


def _positive_limit(value: int | None) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def _organization_override_resolution(org: Organization) -> EntitlementResolution | None:
    plan_name = _normalize(org.plan_type, DEFAULT_PLAN_NAME)
    raw_state = org.plan_status
    state = _normalize(org.plan_status, "restricted")

    if state not in ORGANIZATION_OVERRIDE_STATES:
        return None

    if state == "restricted":
        return EntitlementResolution(
            organization_id=str(org.id),
            source="organization_override",
            subscription_state="restricted",
            raw_subscription_state=raw_state,
            plan_name=plan_name,
            effective_plan=DEFAULT_PLAN_NAME,
            monthly_scan_limit=DEFAULT_PLAN_LIMIT,
            paid_access=False,
            ai_review_notes_allowed=False,
            fail_closed=True,
            reason="organization_restricted_override",
        )

    paid_access = plan_name in PAID_PLAN_NAMES
    effective_plan = plan_name if paid_access else DEFAULT_PLAN_NAME
    monthly_scan_limit = (
        _positive_limit(org.plan_limit) or PLAN_QUOTAS.get(effective_plan, DEFAULT_PLAN_LIMIT)
        if paid_access
        else DEFAULT_PLAN_LIMIT
    )
    return EntitlementResolution(
        organization_id=str(org.id),
        source="organization_override",
        subscription_state="manual_override",
        raw_subscription_state=raw_state,
        plan_name=plan_name,
        effective_plan=effective_plan,
        monthly_scan_limit=monthly_scan_limit,
        paid_access=paid_access,
        ai_review_notes_allowed=paid_access,
        fail_closed=not paid_access,
        reason="organization_manual_override_active" if paid_access else "organization_manual_override_starter",
    )


def _current_subscription(db: Session, org: Organization) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org.id, Subscription.is_current.is_(True))
        .order_by(Subscription.updated_at.desc(), Subscription.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def resolve_entitlement_for_org(
    db: Session,
    org: Organization | None,
) -> EntitlementResolution:
    if org is None:
        return EntitlementResolution(
            organization_id=None,
            source="missing_organization",
            subscription_state="no_subscription",
            raw_subscription_state=None,
            plan_name=DEFAULT_PLAN_NAME,
            effective_plan=DEFAULT_PLAN_NAME,
            monthly_scan_limit=DEFAULT_PLAN_LIMIT,
            paid_access=False,
            ai_review_notes_allowed=False,
            fail_closed=True,
            reason="organization_missing",
        )

    organization_override = _organization_override_resolution(org)
    if organization_override is not None:
        return organization_override

    subscription = _current_subscription(db, org)
    if subscription:
        source = "subscription"
        plan_name = _normalize(subscription.plan_name, DEFAULT_PLAN_NAME)
        raw_state = subscription.status
        state = _normalize(subscription.status, "restricted")
    else:
        source = "legacy_organization"
        plan_name = _normalize(org.plan_type, DEFAULT_PLAN_NAME)
        raw_state = org.plan_status
        state = _normalize(org.plan_status, "restricted")

    if state not in SUBSCRIPTION_STATES:
        return EntitlementResolution(
            organization_id=str(org.id),
            source=source,
            subscription_state="restricted",
            raw_subscription_state=raw_state,
            plan_name=plan_name,
            effective_plan=DEFAULT_PLAN_NAME,
            monthly_scan_limit=DEFAULT_PLAN_LIMIT,
            paid_access=False,
            ai_review_notes_allowed=False,
            fail_closed=True,
            reason="unknown_subscription_state",
        )

    paid_access = plan_name in PAID_PLAN_NAMES and state in ENTITLEMENT_GRANTING_STATES
    effective_plan = plan_name if paid_access else DEFAULT_PLAN_NAME
    monthly_scan_limit = PLAN_QUOTAS.get(effective_plan, DEFAULT_PLAN_LIMIT)
    if source == "legacy_organization" and paid_access:
        monthly_scan_limit = _positive_limit(org.plan_limit) or monthly_scan_limit

    return EntitlementResolution(
        organization_id=str(org.id),
        source=source,
        subscription_state=state,
        raw_subscription_state=raw_state,
        plan_name=plan_name,
        effective_plan=effective_plan,
        monthly_scan_limit=monthly_scan_limit,
        paid_access=paid_access,
        ai_review_notes_allowed=paid_access,
        fail_closed=not paid_access and (state not in {"no_subscription", "checkout_started"}),
        reason=(
            "legacy_organization_entitlement_honored"
            if paid_access and source == "legacy_organization"
            else "paid_entitlement_active"
            if paid_access
            else "starter_safe_entitlement"
        ),
    )
