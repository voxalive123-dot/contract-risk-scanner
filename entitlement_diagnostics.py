from __future__ import annotations

from dataclasses import asdict
from typing import Any
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from entitlement_spine import resolve_entitlement_for_org
from models import (
    BillingCustomerReference,
    MonitoringSignal,
    Organization,
    StripeWebhookEvent,
    Subscription,
)


PAID_PLANS = {"business", "executive", "enterprise"}
ACTIVE_STATES = {"active", "trialing", "manual_override"}


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    return stripped or None


def _serialize_dt(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _legacy_snapshot(org: Organization) -> dict[str, Any]:
    return {
        "plan_type": org.plan_type,
        "plan_status": org.plan_status,
        "plan_limit": org.plan_limit,
        "stripe_customer_id": org.stripe_customer_id,
        "stripe_subscription_id": org.stripe_subscription_id,
        "stripe_price_id": org.stripe_price_id,
        "stripe_price_lookup_key": org.stripe_price_lookup_key,
        "billing_email": org.billing_email,
        "current_period_end": _serialize_dt(org.current_period_end),
    }


def _subscription_snapshot(subscription: Subscription | None) -> dict[str, Any] | None:
    if subscription is None:
        return None

    return {
        "id": str(subscription.id),
        "provider": subscription.provider,
        "external_subscription_id": subscription.external_subscription_id,
        "external_customer_id": subscription.external_customer_id,
        "plan_name": subscription.plan_name,
        "status": subscription.status,
        "current_period_end": _serialize_dt(subscription.current_period_end),
        "cancel_at_period_end": subscription.cancel_at_period_end,
        "is_current": subscription.is_current,
        "source": subscription.source,
        "created_at": _serialize_dt(subscription.created_at),
        "updated_at": _serialize_dt(subscription.updated_at),
    }


def _reference_snapshot(reference: BillingCustomerReference | None) -> dict[str, Any] | None:
    if reference is None:
        return None

    return {
        "id": str(reference.id),
        "provider": reference.provider,
        "external_customer_id": reference.external_customer_id,
        "billing_email": reference.billing_email,
        "created_at": _serialize_dt(reference.created_at),
        "updated_at": _serialize_dt(reference.updated_at),
    }


def _webhook_event_snapshot(event: StripeWebhookEvent) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "stripe_event_id": event.stripe_event_id,
        "event_type": event.event_type,
        "processing_status": event.processing_status,
        "processed_at": _serialize_dt(event.processed_at),
        "stripe_customer_id": event.stripe_customer_id,
        "stripe_subscription_id": event.stripe_subscription_id,
        "stripe_price_lookup_key": event.stripe_price_lookup_key,
        "billing_email": event.billing_email,
        "error": event.error,
    }


def _backfill_signal_snapshot(signal: MonitoringSignal) -> dict[str, Any]:
    return {
        "id": str(signal.id),
        "signal_type": signal.signal_type,
        "severity": signal.severity,
        "message": signal.message,
        "details_json": signal.details_json,
        "created_at": _serialize_dt(signal.created_at),
    }


def _current_subscription(db: Session, org: Organization) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org.id, Subscription.is_current.is_(True))
        .order_by(Subscription.updated_at.desc(), Subscription.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _billing_reference(db: Session, org: Organization) -> BillingCustomerReference | None:
    stmt = (
        select(BillingCustomerReference)
        .where(BillingCustomerReference.org_id == org.id)
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _recent_webhook_events(
    db: Session,
    *,
    org: Organization,
    subscription: Subscription | None,
    reference: BillingCustomerReference | None,
    limit: int,
) -> list[StripeWebhookEvent]:
    identifiers = [
        org.stripe_customer_id,
        org.stripe_subscription_id,
        subscription.external_customer_id if subscription else None,
        subscription.external_subscription_id if subscription else None,
        reference.external_customer_id if reference else None,
    ]
    identifiers = [item for item in identifiers if item]

    filters = [StripeWebhookEvent.org_id == org.id]
    if identifiers:
        filters.extend(
            [
                StripeWebhookEvent.stripe_customer_id.in_(identifiers),
                StripeWebhookEvent.stripe_subscription_id.in_(identifiers),
            ]
        )

    stmt = (
        select(StripeWebhookEvent)
        .where(or_(*filters))
        .order_by(StripeWebhookEvent.processed_at.desc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def _backfill_signals(db: Session, org: Organization) -> list[MonitoringSignal]:
    stmt = (
        select(MonitoringSignal)
        .where(
            MonitoringSignal.org_id == org.id,
            MonitoringSignal.category == "billing_backfill",
        )
        .order_by(MonitoringSignal.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def _customer_conflicts(
    db: Session,
    *,
    org: Organization,
    reference: BillingCustomerReference | None,
) -> list[str]:
    ids = {org.stripe_customer_id, reference.external_customer_id if reference else None}
    conflicts: list[str] = []
    for customer_id in [item for item in ids if item]:
        stmt = (
            select(BillingCustomerReference)
            .where(
                BillingCustomerReference.provider == "stripe",
                BillingCustomerReference.external_customer_id == customer_id,
                BillingCustomerReference.org_id != org.id,
            )
        )
        for row in db.execute(stmt).scalars().all():
            conflicts.append(str(row.org_id))
    return sorted(set(conflicts))


def _subscription_conflicts(
    db: Session,
    *,
    org: Organization,
    subscription: Subscription | None,
) -> list[str]:
    ids = {org.stripe_subscription_id, subscription.external_subscription_id if subscription else None}
    conflicts: list[str] = []
    for subscription_id in [item for item in ids if item]:
        stmt = (
            select(Subscription)
            .where(
                Subscription.provider == "stripe",
                Subscription.external_subscription_id == subscription_id,
                Subscription.org_id != org.id,
            )
        )
        for row in db.execute(stmt).scalars().all():
            conflicts.append(str(row.org_id))
    return sorted(set(conflicts))


def _mismatch_flags(
    db: Session,
    *,
    org: Organization,
    subscription: Subscription | None,
    reference: BillingCustomerReference | None,
    entitlement: dict[str, Any],
) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    legacy_plan = _normalize(org.plan_type)
    legacy_status = _normalize(org.plan_status)
    legacy_paid = legacy_plan in PAID_PLANS and legacy_status in ACTIVE_STATES

    if legacy_paid and subscription is None:
        flags.append(
            {
                "code": "legacy_paid_without_current_subscription",
                "severity": "warning",
                "message": "Legacy Organisation fields indicate paid access, but no current Phase 10 Subscription exists.",
            }
        )

    if subscription and subscription.status in ACTIVE_STATES and reference is None:
        flags.append(
            {
                "code": "active_subscription_missing_customer_reference",
                "severity": "warning",
                "message": "Current active Subscription exists without a Billing Customer Reference.",
            }
        )

    if subscription and org.stripe_subscription_id and subscription.external_subscription_id:
        if org.stripe_subscription_id != subscription.external_subscription_id:
            flags.append(
                {
                    "code": "legacy_subscription_id_mismatch",
                    "severity": "warning",
                    "message": "Legacy Organisation subscription ID differs from current Subscription truth.",
                }
            )

    if reference and org.stripe_customer_id and reference.external_customer_id:
        if org.stripe_customer_id != reference.external_customer_id:
            flags.append(
                {
                    "code": "legacy_customer_id_mismatch",
                    "severity": "warning",
                    "message": "Legacy Organisation customer ID differs from Billing Customer Reference truth.",
                }
            )

    for conflict_org_id in _customer_conflicts(db, org=org, reference=reference):
        flags.append(
            {
                "code": "stripe_customer_id_conflicts_across_orgs",
                "severity": "critical",
                "message": f"Stripe customer ID also maps to organisation {conflict_org_id}.",
            }
        )

    for conflict_org_id in _subscription_conflicts(db, org=org, subscription=subscription):
        flags.append(
            {
                "code": "stripe_subscription_id_conflicts_across_orgs",
                "severity": "critical",
                "message": f"Stripe subscription ID also maps to organisation {conflict_org_id}.",
            }
        )

    if legacy_paid and entitlement["effective_plan"] == "starter":
        flags.append(
            {
                "code": "legacy_paid_but_resolver_starter_safe",
                "severity": "info",
                "message": "Resolver is correctly ignoring legacy paid fields without current Subscription truth.",
            }
        )

    if subscription and subscription.plan_name in PAID_PLANS and subscription.status in ACTIVE_STATES:
        if entitlement["effective_plan"] != subscription.plan_name:
            flags.append(
                {
                    "code": "resolver_inconsistent_with_subscription",
                    "severity": "critical",
                    "message": "Resolver effective plan does not match active current Subscription.",
                }
            )

    return flags


def build_entitlement_diagnostics(
    db: Session,
    *,
    org_id: uuid.UUID | str,
    webhook_limit: int = 5,
) -> dict[str, Any]:
    parsed_org_id = org_id if isinstance(org_id, uuid.UUID) else uuid.UUID(str(org_id))
    org = db.get(Organization, parsed_org_id)
    if org is None:
        return {
            "org_id": str(parsed_org_id),
            "found": False,
            "read_only": True,
            "mismatch_flags": [
                {
                    "code": "organization_not_found",
                    "severity": "critical",
                    "message": "No Organisation exists for the requested ID.",
                }
            ],
        }

    subscription = _current_subscription(db, org)
    reference = _billing_reference(db, org)
    resolution = resolve_entitlement_for_org(db, org)
    entitlement = asdict(resolution)
    webhooks = _recent_webhook_events(
        db,
        org=org,
        subscription=subscription,
        reference=reference,
        limit=webhook_limit,
    )
    backfill_signals = _backfill_signals(db, org)

    return {
        "org_id": str(org.id),
        "found": True,
        "read_only": True,
        "legacy_organization_billing": _legacy_snapshot(org),
        "phase_10_subscription": _subscription_snapshot(subscription),
        "billing_customer_reference": _reference_snapshot(reference),
        "effective_entitlement": entitlement,
        "effective_ai_entitlement": {
            "ai_review_notes_allowed": resolution.ai_review_notes_allowed,
            "source": "resolver",
            "effective_plan": resolution.effective_plan,
        },
        "effective_quota": {
            "monthly_scan_limit": resolution.monthly_scan_limit,
            "source": "resolver",
            "effective_plan": resolution.effective_plan,
        },
        "last_webhook_events": [_webhook_event_snapshot(event) for event in webhooks],
        "backfill": {
            "was_backfilled": bool(backfill_signals),
            "signals": [_backfill_signal_snapshot(signal) for signal in backfill_signals],
        },
        "mismatch_flags": _mismatch_flags(
            db,
            org=org,
            subscription=subscription,
            reference=reference,
            entitlement=entitlement,
        ),
    }
