from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db import Base
from entitlement_diagnostics import build_entitlement_diagnostics
from legacy_billing_backfill import backfill_legacy_billing_for_org
from models import (
    BillingCustomerReference,
    MonitoringSignal,
    Organization,
    StripeWebhookEvent,
    Subscription,
)


@pytest.fixture
def diagnostics_session(tmp_path):
    db_path = tmp_path / "entitlement_diagnostics.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    try:
        yield SessionLocal
    finally:
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_org(
    session_factory,
    *,
    plan_type: str = "starter",
    plan_status: str = "active",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
):
    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status=plan_status,
            plan_limit=1000,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_lookup_key=f"{plan_type}_monthly_gbp" if plan_type != "starter" else None,
            billing_email="billing@example.test" if stripe_customer_id else None,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org.id


def add_subscription(
    session_factory,
    *,
    org_id,
    plan_name: str,
    status: str,
    customer_id: str = "cus_diag",
    subscription_id: str = "sub_diag",
    source: str = "stripe_webhook",
):
    with session_factory() as db:
        db.add(
            Subscription(
                org_id=org_id,
                provider="stripe",
                external_subscription_id=subscription_id,
                external_customer_id=customer_id,
                plan_name=plan_name,
                status=status,
                is_current=True,
                source=source,
            )
        )
        db.commit()


def add_reference(session_factory, *, org_id, customer_id: str = "cus_diag"):
    with session_factory() as db:
        db.add(
            BillingCustomerReference(
                org_id=org_id,
                provider="stripe",
                external_customer_id=customer_id,
                billing_email="billing@example.test",
            )
        )
        db.commit()


def test_active_paid_org_diagnostics_explain_resolver_backed_access(diagnostics_session):
    org_id = create_org(
        diagnostics_session,
        plan_type="business",
        plan_status="active",
        stripe_customer_id="cus_paid",
        stripe_subscription_id="sub_paid",
    )
    add_subscription(
        diagnostics_session,
        org_id=org_id,
        plan_name="business",
        status="active",
        customer_id="cus_paid",
        subscription_id="sub_paid",
    )
    add_reference(diagnostics_session, org_id=org_id, customer_id="cus_paid")
    with diagnostics_session() as db:
        db.add(
            StripeWebhookEvent(
                stripe_event_id="evt_paid",
                event_type="customer.subscription.updated",
                processing_status="processed",
                org_id=org_id,
                stripe_customer_id="cus_paid",
                stripe_subscription_id="sub_paid",
                stripe_price_lookup_key="business_monthly_gbp",
            )
        )
        db.commit()

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    assert report["read_only"] is True
    assert report["effective_entitlement"]["effective_plan"] == "business"
    assert report["effective_entitlement"]["paid_access"] is True
    assert report["effective_ai_entitlement"]["ai_review_notes_allowed"] is True
    assert report["effective_quota"]["monthly_scan_limit"] == 100
    assert report["phase_10_subscription"]["source"] == "stripe_webhook"
    assert report["billing_customer_reference"]["external_customer_id"] == "cus_paid"
    assert report["last_webhook_events"][0]["stripe_event_id"] == "evt_paid"
    assert report["mismatch_flags"] == []


def test_starter_no_subscription_diagnostics(diagnostics_session):
    org_id = create_org(diagnostics_session)

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    assert report["phase_10_subscription"] is None
    assert report["billing_customer_reference"] is None
    assert report["effective_entitlement"]["effective_plan"] == "starter"
    assert report["effective_ai_entitlement"]["ai_review_notes_allowed"] is False
    assert report["effective_quota"]["monthly_scan_limit"] == 5
    assert report["mismatch_flags"] == []


def test_legacy_paid_without_subscription_is_flagged(diagnostics_session):
    org_id = create_org(
        diagnostics_session,
        plan_type="enterprise",
        plan_status="active",
        stripe_customer_id="cus_legacy_only",
        stripe_subscription_id="sub_legacy_only",
    )

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    codes = {flag["code"] for flag in report["mismatch_flags"]}
    assert "legacy_paid_without_current_subscription" in codes
    assert "legacy_paid_but_resolver_starter_safe" not in codes
    assert report["effective_entitlement"]["effective_plan"] == "enterprise"


def test_active_subscription_missing_customer_reference_is_flagged(diagnostics_session):
    org_id = create_org(diagnostics_session)
    add_subscription(
        diagnostics_session,
        org_id=org_id,
        plan_name="executive",
        status="active",
        customer_id="cus_missing_ref",
        subscription_id="sub_missing_ref",
    )

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    codes = {flag["code"] for flag in report["mismatch_flags"]}
    assert "active_subscription_missing_customer_reference" in codes
    assert report["effective_entitlement"]["effective_plan"] == "executive"


def test_backfilled_org_diagnostics_show_source_and_audit_signal(diagnostics_session):
    org_id = create_org(
        diagnostics_session,
        plan_type="business",
        plan_status="active",
        stripe_customer_id="cus_backfilled_diag",
        stripe_subscription_id="sub_backfilled_diag",
    )

    with diagnostics_session() as db:
        org = db.get(Organization, org_id)
        backfill_legacy_billing_for_org(db, org, dry_run=False)

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    assert report["backfill"]["was_backfilled"] is True
    assert report["phase_10_subscription"]["source"] == "legacy_backfill"
    signal = report["backfill"]["signals"][0]
    assert signal["signal_type"] == "legacy_backfill_applied"
    assert json.loads(signal["details_json"])["method"] == "legacy_backfill"


def test_diagnostics_are_read_only(diagnostics_session):
    org_id = create_org(
        diagnostics_session,
        plan_type="enterprise",
        plan_status="active",
        stripe_customer_id="cus_read_only",
        stripe_subscription_id="sub_read_only",
    )

    with diagnostics_session() as db:
        before = {
            "subscriptions": len(db.execute(select(Subscription)).scalars().all()),
            "references": len(db.execute(select(BillingCustomerReference)).scalars().all()),
            "signals": len(db.execute(select(MonitoringSignal)).scalars().all()),
        }
        report = build_entitlement_diagnostics(db, org_id=org_id)
        after = {
            "subscriptions": len(db.execute(select(Subscription)).scalars().all()),
            "references": len(db.execute(select(BillingCustomerReference)).scalars().all()),
            "signals": len(db.execute(select(MonitoringSignal)).scalars().all()),
        }

    assert report["read_only"] is True
    assert before == after


def test_stripe_identifier_conflicts_are_flagged(diagnostics_session):
    org_id = create_org(
        diagnostics_session,
        stripe_customer_id="cus_conflict_diag",
        stripe_subscription_id="sub_conflict_diag",
    )
    other_org_id = create_org(diagnostics_session)
    add_reference(diagnostics_session, org_id=other_org_id, customer_id="cus_conflict_diag")
    add_subscription(
        diagnostics_session,
        org_id=other_org_id,
        plan_name="business",
        status="active",
        customer_id="cus_other",
        subscription_id="sub_conflict_diag",
    )

    with diagnostics_session() as db:
        report = build_entitlement_diagnostics(db, org_id=org_id)

    codes = {flag["code"] for flag in report["mismatch_flags"]}
    assert "stripe_customer_id_conflicts_across_orgs" in codes
    assert "stripe_subscription_id_conflicts_across_orgs" in codes
