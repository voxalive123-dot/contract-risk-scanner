from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from models import (
    BillingCustomerReference,
    MonitoringSignal,
    Organization,
    Subscription,
)
from stripe_billing import PAID_ACTIVE_STATUSES, RESTRICTED_STATUSES


PAID_PLANS = {"business", "executive", "enterprise"}
BACKFILL_ALLOWED_STATUSES = PAID_ACTIVE_STATUSES | RESTRICTED_STATUSES
BackfillAction = Literal["backfilled", "dry_run", "skipped", "manual_review"]


@dataclass(frozen=True)
class LegacyBillingSnapshot:
    plan_type: str | None
    plan_status: str | None
    plan_limit: int | None
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    stripe_price_id: str | None
    stripe_price_lookup_key: str | None
    billing_email: str | None


@dataclass(frozen=True)
class LegacyBackfillDecision:
    org_id: str
    action: BackfillAction
    eligible: bool
    reason: str
    legacy: LegacyBillingSnapshot
    subscription_id: str | None = None
    billing_customer_reference_id: str | None = None


def _normalize(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip().lower()
    return stripped or None


def _snapshot(org: Organization) -> LegacyBillingSnapshot:
    return LegacyBillingSnapshot(
        plan_type=org.plan_type,
        plan_status=org.plan_status,
        plan_limit=org.plan_limit,
        stripe_customer_id=org.stripe_customer_id,
        stripe_subscription_id=org.stripe_subscription_id,
        stripe_price_id=org.stripe_price_id,
        stripe_price_lookup_key=org.stripe_price_lookup_key,
        billing_email=org.billing_email,
    )


def _existing_current_subscription(db: Session, org: Organization) -> Subscription | None:
    stmt = (
        select(Subscription)
        .where(Subscription.org_id == org.id, Subscription.is_current.is_(True))
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def _customer_id_used_by_other_org(db: Session, org: Organization, customer_id: str) -> bool:
    stmt = (
        select(BillingCustomerReference)
        .where(
            BillingCustomerReference.provider == "stripe",
            BillingCustomerReference.external_customer_id == customer_id,
            BillingCustomerReference.org_id != org.id,
        )
        .limit(1)
    )
    return db.execute(stmt).scalars().first() is not None


def _subscription_id_used_by_other_org(db: Session, org: Organization, subscription_id: str) -> bool:
    stmt = (
        select(Subscription)
        .where(
            Subscription.provider == "stripe",
            Subscription.external_subscription_id == subscription_id,
            Subscription.org_id != org.id,
        )
        .limit(1)
    )
    return db.execute(stmt).scalars().first() is not None


def _manual_review(org: Organization, reason: str) -> LegacyBackfillDecision:
    return LegacyBackfillDecision(
        org_id=str(org.id),
        action="manual_review",
        eligible=False,
        reason=reason,
        legacy=_snapshot(org),
    )


def evaluate_legacy_billing_backfill(
    db: Session,
    org: Organization,
) -> LegacyBackfillDecision:
    plan_type = _normalize(org.plan_type)
    plan_status = _normalize(org.plan_status)

    if plan_type not in PAID_PLANS:
        return LegacyBackfillDecision(
            org_id=str(org.id),
            action="skipped",
            eligible=False,
            reason="legacy_plan_not_paid",
            legacy=_snapshot(org),
        )

    if plan_status not in BACKFILL_ALLOWED_STATUSES:
        return _manual_review(org, "legacy_status_not_recognized_for_backfill")

    if not org.stripe_customer_id or not org.stripe_subscription_id:
        return _manual_review(org, "missing_legacy_customer_or_subscription_id")

    if _customer_id_used_by_other_org(db, org, org.stripe_customer_id):
        return _manual_review(org, "stripe_customer_id_already_mapped_to_other_org")

    if _subscription_id_used_by_other_org(db, org, org.stripe_subscription_id):
        return _manual_review(org, "stripe_subscription_id_already_mapped_to_other_org")

    current_subscription = _existing_current_subscription(db, org)
    if current_subscription and (
        current_subscription.external_subscription_id != org.stripe_subscription_id
        or current_subscription.plan_name != plan_type
        or current_subscription.status != plan_status
    ):
        return _manual_review(org, "current_subscription_conflicts_with_legacy_fields")

    return LegacyBackfillDecision(
        org_id=str(org.id),
        action="dry_run",
        eligible=True,
        reason="eligible_legacy_paid_org",
        legacy=_snapshot(org),
    )


def _upsert_reference(db: Session, org: Organization) -> BillingCustomerReference:
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
            external_customer_id=org.stripe_customer_id,
        )
        db.add(reference)

    reference.external_customer_id = org.stripe_customer_id
    reference.billing_email = org.billing_email
    return reference


def _upsert_subscription(db: Session, org: Organization) -> Subscription:
    subscription = _existing_current_subscription(db, org)
    if subscription is None:
        subscription = Subscription(
            org_id=org.id,
            provider="stripe",
            external_subscription_id=org.stripe_subscription_id,
            source="legacy_backfill",
        )
        db.add(subscription)

    subscription.external_subscription_id = org.stripe_subscription_id
    subscription.external_customer_id = org.stripe_customer_id
    subscription.plan_name = _normalize(org.plan_type) or "starter"
    subscription.status = _normalize(org.plan_status) or "restricted"
    subscription.current_period_end = org.current_period_end
    subscription.is_current = True
    subscription.source = "legacy_backfill"
    return subscription


def _write_audit_signal(
    db: Session,
    *,
    org: Organization,
    decision: LegacyBackfillDecision,
    subscription: Subscription,
    reference: BillingCustomerReference,
) -> None:
    details = {
        "method": "legacy_backfill",
        "legacy": asdict(decision.legacy),
        "subscription": {
            "id": str(subscription.id),
            "external_subscription_id": subscription.external_subscription_id,
            "plan_name": subscription.plan_name,
            "status": subscription.status,
            "source": subscription.source,
        },
        "billing_customer_reference": {
            "id": str(reference.id),
            "provider": reference.provider,
            "external_customer_id": reference.external_customer_id,
        },
    }
    db.add(
        MonitoringSignal(
            org_id=org.id,
            category="billing_backfill",
            signal_type="legacy_backfill_applied",
            severity="info",
            message="Legacy Organisation billing fields were backfilled into Phase 10 subscription truth.",
            details_json=json.dumps(details, sort_keys=True),
        )
    )


def backfill_legacy_billing_for_org(
    db: Session,
    org: Organization,
    *,
    dry_run: bool = True,
) -> LegacyBackfillDecision:
    decision = evaluate_legacy_billing_backfill(db, org)

    if not decision.eligible:
        return decision

    if dry_run:
        return decision

    reference = _upsert_reference(db, org)
    subscription = _upsert_subscription(db, org)
    db.flush()

    applied = LegacyBackfillDecision(
        org_id=str(org.id),
        action="backfilled",
        eligible=True,
        reason="legacy_paid_org_backfilled",
        legacy=decision.legacy,
        subscription_id=str(subscription.id),
        billing_customer_reference_id=str(reference.id),
    )
    _write_audit_signal(
        db,
        org=org,
        decision=applied,
        subscription=subscription,
        reference=reference,
    )
    db.commit()
    return applied


def backfill_legacy_billing(
    db: Session,
    *,
    dry_run: bool = True,
) -> list[LegacyBackfillDecision]:
    orgs = db.execute(select(Organization).order_by(Organization.created_at.asc())).scalars().all()
    return [
        backfill_legacy_billing_for_org(db, org, dry_run=dry_run)
        for org in orgs
    ]
