from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from db import Base
from entitlement_spine import resolve_entitlement_for_org
from legacy_billing_backfill import (
    backfill_legacy_billing,
    backfill_legacy_billing_for_org,
)
from models import BillingCustomerReference, MonitoringSignal, Organization, Subscription


@pytest.fixture
def backfill_session(tmp_path):
    db_path = tmp_path / "legacy_backfill.sqlite"
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
    name: str | None = None,
):
    with session_factory() as db:
        org = Organization(
            name=name or f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status=plan_status,
            plan_limit=1000,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            stripe_price_id="price_test" if stripe_subscription_id else None,
            stripe_price_lookup_key=f"{plan_type}_monthly_gbp" if plan_type != "starter" else None,
            billing_email="billing@example.test" if stripe_customer_id else None,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org.id


def test_eligible_legacy_paid_org_backfills_phase_10_truth(backfill_session):
    org_id = create_org(
        backfill_session,
        plan_type="business",
        plan_status="active",
        stripe_customer_id="cus_backfill",
        stripe_subscription_id="sub_backfill",
    )

    with backfill_session() as db:
        org = db.get(Organization, org_id)
        decision = backfill_legacy_billing_for_org(db, org, dry_run=False)

    assert decision.action == "backfilled"
    assert decision.eligible is True

    with backfill_session() as db:
        subscription = db.execute(select(Subscription)).scalars().first()
        reference = db.execute(select(BillingCustomerReference)).scalars().first()
        signal = db.execute(select(MonitoringSignal)).scalars().first()

        assert subscription is not None
        assert subscription.org_id == org_id
        assert subscription.plan_name == "business"
        assert subscription.status == "active"
        assert subscription.external_subscription_id == "sub_backfill"
        assert subscription.source == "legacy_backfill"

        assert reference is not None
        assert reference.org_id == org_id
        assert reference.external_customer_id == "cus_backfill"

        assert signal is not None
        assert signal.org_id == org_id
        assert signal.category == "billing_backfill"
        assert signal.signal_type == "legacy_backfill_applied"
        details = json.loads(signal.details_json)
        assert details["method"] == "legacy_backfill"
        assert details["legacy"]["plan_type"] == "business"
        assert details["subscription"]["external_subscription_id"] == "sub_backfill"

        entitlement = resolve_entitlement_for_org(db, db.get(Organization, org_id))
        assert entitlement.effective_plan == "business"
        assert entitlement.ai_review_notes_allowed is True


def test_dry_run_reports_without_mutating(backfill_session):
    org_id = create_org(
        backfill_session,
        plan_type="executive",
        plan_status="active",
        stripe_customer_id="cus_dry",
        stripe_subscription_id="sub_dry",
    )

    with backfill_session() as db:
        org = db.get(Organization, org_id)
        decision = backfill_legacy_billing_for_org(db, org, dry_run=True)

    assert decision.action == "dry_run"
    assert decision.eligible is True

    with backfill_session() as db:
        assert db.execute(select(Subscription)).scalars().all() == []
        assert db.execute(select(BillingCustomerReference)).scalars().all() == []
        assert db.execute(select(MonitoringSignal)).scalars().all() == []
        entitlement = resolve_entitlement_for_org(db, db.get(Organization, org_id))
        assert entitlement.source == "legacy_organization"
        assert entitlement.effective_plan == "executive"


def test_ambiguous_missing_subscription_id_flagged_for_manual_review(backfill_session):
    org_id = create_org(
        backfill_session,
        plan_type="enterprise",
        plan_status="active",
        stripe_customer_id="cus_ambiguous",
        stripe_subscription_id=None,
    )

    with backfill_session() as db:
        org = db.get(Organization, org_id)
        decision = backfill_legacy_billing_for_org(db, org, dry_run=False)

    assert decision.action == "manual_review"
    assert decision.eligible is False
    assert decision.reason == "missing_legacy_customer_or_subscription_id"

    with backfill_session() as db:
        assert db.execute(select(Subscription)).scalars().all() == []
        assert db.execute(select(BillingCustomerReference)).scalars().all() == []


def test_ambiguous_conflicting_subscription_record_flagged_for_manual_review(backfill_session):
    org_id = create_org(
        backfill_session,
        plan_type="business",
        plan_status="active",
        stripe_customer_id="cus_conflict",
        stripe_subscription_id="sub_legacy",
    )

    with backfill_session() as db:
        db.add(
            Subscription(
                org_id=org_id,
                provider="stripe",
                external_subscription_id="sub_different",
                external_customer_id="cus_conflict",
                plan_name="business",
                status="active",
                is_current=True,
                source="test",
            )
        )
        db.commit()

    with backfill_session() as db:
        org = db.get(Organization, org_id)
        decision = backfill_legacy_billing_for_org(db, org, dry_run=False)

    assert decision.action == "manual_review"
    assert decision.reason == "current_subscription_conflicts_with_legacy_fields"


def test_starter_legacy_org_does_not_get_premium_truth(backfill_session):
    org_id = create_org(
        backfill_session,
        plan_type="starter",
        plan_status="active",
        stripe_customer_id="cus_starter",
        stripe_subscription_id="sub_starter",
    )

    with backfill_session() as db:
        org = db.get(Organization, org_id)
        decision = backfill_legacy_billing_for_org(db, org, dry_run=False)

    assert decision.action == "skipped"
    assert decision.reason == "legacy_plan_not_paid"

    with backfill_session() as db:
        assert db.execute(select(Subscription)).scalars().all() == []
        entitlement = resolve_entitlement_for_org(db, db.get(Organization, org_id))
        assert entitlement.effective_plan == "starter"
        assert entitlement.ai_review_notes_allowed is False


def test_batch_backfill_reports_each_org_decision(backfill_session):
    create_org(
        backfill_session,
        plan_type="business",
        plan_status="active",
        stripe_customer_id="cus_batch_paid",
        stripe_subscription_id="sub_batch_paid",
        name="batch-paid",
    )
    create_org(
        backfill_session,
        plan_type="starter",
        plan_status="active",
        name="batch-starter",
    )

    with backfill_session() as db:
        decisions = backfill_legacy_billing(db, dry_run=True)

    assert [decision.action for decision in decisions] == ["dry_run", "skipped"]
