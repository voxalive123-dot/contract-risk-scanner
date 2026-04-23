from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    BillingCustomerReference,
    Organization,
    StripeWebhookEvent,
    Subscription,
)
from stripe_billing import (
    PAID_ACTIVE_STATUSES,
    RESTRICTED_STATUSES,
    apply_default_entitlement,
    apply_paid_entitlement,
    bind_billing_identity,
    extract_event_context,
    map_lookup_key_to_plan,
    resolve_org_match,
)


SUPPORTED_BILLING_EVENTS = {
    "checkout.session.completed",
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
}


@dataclass(frozen=True)
class StripeReconciliationResult:
    processing_status: str
    org: Organization | None
    event_row: StripeWebhookEvent
    error: str | None = None


def _lookup_billing_customer_reference(
    db: Session,
    *,
    stripe_customer_id: str | None,
) -> Organization | None:
    if not stripe_customer_id:
        return None

    stmt = (
        select(BillingCustomerReference)
        .where(
            BillingCustomerReference.provider == "stripe",
            BillingCustomerReference.external_customer_id == stripe_customer_id,
        )
        .limit(1)
    )
    reference = db.execute(stmt).scalars().first()
    if not reference:
        return None

    return db.get(Organization, reference.org_id)


def _resolve_org(
    db: Session,
    *,
    context: dict[str, Any],
) -> Organization | None:
    org = resolve_org_match(
        db,
        metadata_org_id=context.get("metadata_org_id"),
        stripe_customer_id=context.get("customer_id"),
        stripe_subscription_id=context.get("subscription_id"),
    )
    if org:
        return org

    return _lookup_billing_customer_reference(
        db,
        stripe_customer_id=context.get("customer_id"),
    )


def _upsert_billing_customer_reference(
    db: Session,
    *,
    org: Organization,
    context: dict[str, Any],
) -> None:
    customer_id = context.get("customer_id")
    if not customer_id:
        return

    stmt = (
        select(BillingCustomerReference)
        .where(BillingCustomerReference.org_id == org.id)
        .limit(1)
    )
    reference = db.execute(stmt).scalars().first()
    if reference is None:
        reference = BillingCustomerReference(
            org_id=org.id,
            provider="stripe",
            external_customer_id=customer_id,
        )
        db.add(reference)

    reference.external_customer_id = customer_id
    if context.get("billing_email"):
        reference.billing_email = context["billing_email"]


def _upsert_subscription(
    db: Session,
    *,
    org: Organization,
    context: dict[str, Any],
    plan_name: str,
    subscription_status: str,
    source: str,
) -> Subscription:
    subscription_id = context.get("subscription_id")
    subscription: Subscription | None = None

    if subscription_id:
        stmt = (
            select(Subscription)
            .where(
                Subscription.provider == "stripe",
                Subscription.external_subscription_id == subscription_id,
            )
            .limit(1)
        )
        subscription = db.execute(stmt).scalars().first()

    if subscription is None:
        stmt = (
            select(Subscription)
            .where(Subscription.org_id == org.id, Subscription.is_current.is_(True))
            .limit(1)
        )
        subscription = db.execute(stmt).scalars().first()

    if subscription is None:
        subscription = Subscription(
            org_id=org.id,
            provider="stripe",
            external_subscription_id=subscription_id,
            source=source,
        )
        db.add(subscription)

    subscription.external_subscription_id = subscription_id
    subscription.external_customer_id = context.get("customer_id")
    subscription.plan_name = plan_name
    subscription.status = subscription_status
    subscription.current_period_end = context.get("current_period_end")
    subscription.is_current = True
    subscription.source = source
    return subscription


def _reconcile_org_state_for_current_runtime(
    db: Session,
    *,
    org: Organization,
    plan_name: str | None,
    subscription_status: str | None,
    context: dict[str, Any],
) -> tuple[str, str | None]:
    if subscription_status in PAID_ACTIVE_STATUSES:
        if plan_name is None:
            bind_billing_identity(org, context)
            return "unmatched", "Unable to determine VoxaRisk plan from Stripe price lookup key."
        apply_paid_entitlement(
            db,
            org,
            plan_name=plan_name,
            subscription_status=subscription_status,
            context=context,
        )
        return "processed", None

    if subscription_status in RESTRICTED_STATUSES:
        apply_default_entitlement(
            db,
            org,
            subscription_status=subscription_status,
            context=context,
        )
        return "processed", None

    if subscription_status == "checkout_started":
        bind_billing_identity(org, context)
        return "checkout_started", None

    bind_billing_identity(org, context)
    return "ignored", f"Unsupported subscription status: {subscription_status or 'missing'}"


def reconcile_stripe_event(
    db: Session,
    *,
    event_id: str,
    event_type: str,
    payload_object: dict[str, Any],
) -> StripeReconciliationResult:
    context = extract_event_context(event_type, payload_object)
    org = _resolve_org(db, context=context)
    plan_name = map_lookup_key_to_plan(context.get("price_lookup_key"))
    subscription_status = context.get("subscription_status")

    processing_status = "processed"
    error: str | None = None

    if event_type not in SUPPORTED_BILLING_EVENTS:
        processing_status = "ignored"
        error = f"Unsupported Stripe event type: {event_type}"
    elif org is None:
        processing_status = "unmatched"
        error = "No deterministic organization mapping found."
    elif event_type == "checkout.session.completed":
        _upsert_billing_customer_reference(db, org=org, context=context)
        bind_billing_identity(org, context)
        processing_status = "checkout_started"
        subscription_status = "checkout_started"
        if context.get("subscription_id"):
            _upsert_subscription(
                db,
                org=org,
                context=context,
                plan_name=plan_name or "starter",
                subscription_status=subscription_status,
                source=event_type,
            )
    else:
        if not subscription_status:
            processing_status = "unmatched"
            error = "Subscription status missing from Stripe event."
        else:
            compatibility_status, compatibility_error = _reconcile_org_state_for_current_runtime(
                db,
                org=org,
                plan_name=plan_name,
                subscription_status=subscription_status,
                context=context,
            )
            processing_status = compatibility_status
            error = compatibility_error

            if plan_name is not None or subscription_status in RESTRICTED_STATUSES:
                _upsert_billing_customer_reference(db, org=org, context=context)
                _upsert_subscription(
                    db,
                    org=org,
                    context=context,
                    plan_name=plan_name or "starter",
                    subscription_status=subscription_status,
                    source=event_type,
                )

    event_row = StripeWebhookEvent(
        stripe_event_id=event_id,
        event_type=event_type,
        processing_status=processing_status,
        org_id=org.id if org else None,
        stripe_customer_id=context.get("customer_id"),
        stripe_subscription_id=context.get("subscription_id"),
        stripe_price_id=context.get("price_id"),
        stripe_price_lookup_key=context.get("price_lookup_key"),
        billing_email=context.get("billing_email"),
        error=error,
    )
    db.add(event_row)
    db.commit()

    return StripeReconciliationResult(
        processing_status=processing_status,
        org=org,
        event_row=event_row,
        error=error,
    )
