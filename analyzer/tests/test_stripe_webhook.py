from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import api
from db import Base
from models import BillingCustomerReference, Organization, StripeWebhookEvent, Subscription
from stripe_billing import map_lookup_key_to_plan


@pytest.fixture
def stripe_test_client(tmp_path):
    db_path = tmp_path / "stripe_webhook.sqlite"
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    api.app.dependency_overrides[api.get_db] = override_get_db
    client = TestClient(api.app)

    try:
        yield client, SessionLocal
    finally:
        api.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_org(
    session_factory,
    *,
    name: str = "org-under-test",
    plan_type: str = "starter",
    plan_limit: int = 1000,
    plan_status: str = "active",
    stripe_customer_id: str | None = None,
    stripe_subscription_id: str | None = None,
):
    with session_factory() as db:
        org = Organization(
            name=name,
            plan_type=plan_type,
            plan_limit=plan_limit,
            plan_status=plan_status,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        org_id = org.id
    return org_id


def test_plan_lookup_key_maps_correctly():
    assert map_lookup_key_to_plan("business_monthly_gbp") == "business"
    assert map_lookup_key_to_plan("business_yearly_gbp") == "business"
    assert map_lookup_key_to_plan("executive_monthly_gbp") == "executive"
    assert map_lookup_key_to_plan("executive_yearly_gbp") == "executive"
    assert map_lookup_key_to_plan("enterprise_monthly_gbp") == "enterprise"
    assert map_lookup_key_to_plan("enterprise_yearly_gbp") == "enterprise"
    assert map_lookup_key_to_plan("unknown_lookup_key") is None


def test_invalid_signature_rejected(stripe_test_client, monkeypatch):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    def raise_signature_error(*args, **kwargs):
        raise api.stripe.error.SignatureVerificationError(
            "invalid signature",
            "Stripe-Signature",
        )

    monkeypatch.setattr(api.stripe.Webhook, "construct_event", raise_signature_error)

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "bad"},
    )

    assert response.status_code == 400

    with session_factory() as db:
        count = db.execute(select(StripeWebhookEvent)).scalars().all()
        assert count == []


def test_duplicate_event_is_idempotent(stripe_test_client, monkeypatch):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    with session_factory() as db:
        db.add(
            StripeWebhookEvent(
                stripe_event_id="evt_duplicate",
                event_type="customer.subscription.updated",
                processing_status="processed",
            )
        )
        db.commit()

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": "evt_duplicate",
            "type": "customer.subscription.updated",
            "data": {"object": {}},
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "duplicate"

    with session_factory() as db:
        events = db.execute(select(StripeWebhookEvent)).scalars().all()
        subscriptions = db.execute(select(Subscription)).scalars().all()
        assert len(events) == 1
        assert subscriptions == []


def test_unmatched_checkout_does_not_upgrade_org(stripe_test_client, monkeypatch):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    org_id = create_org(session_factory, name="unmatched-org")

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": "evt_unmatched_checkout",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_unmatched",
                    "subscription": "sub_unmatched",
                    "customer_details": {"email": "billing@unmatched.test"},
                    "metadata": {},
                }
            },
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unmatched"

    with session_factory() as db:
        org = db.get(Organization, org_id)
        assert org is not None
        assert org.plan_type == "starter"
        assert org.plan_status == "active"
        assert org.stripe_customer_id is None

        event = db.execute(
            select(StripeWebhookEvent).where(
                StripeWebhookEvent.stripe_event_id == "evt_unmatched_checkout"
            )
        ).scalars().first()
        assert event is not None
        assert event.processing_status == "unmatched"
        assert event.org_id is None
        assert event.billing_email == "billing@unmatched.test"

        subscriptions = db.execute(select(Subscription)).scalars().all()
        assert subscriptions == []


def test_matched_subscription_updates_org_plan(stripe_test_client, monkeypatch):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    org_id = create_org(session_factory, name="matched-org")

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": "evt_matched_subscription",
            "type": "customer.subscription.created",
            "data": {
                "object": {
                    "id": "sub_business_1",
                    "customer": "cus_business_1",
                    "status": "active",
                    "current_period_end": 1_800_000_000,
                    "metadata": {"org_id": str(org_id)},
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_business_monthly",
                                    "lookup_key": "business_monthly_gbp",
                                }
                            }
                        ]
                    },
                }
            },
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    with session_factory() as db:
        org = db.get(Organization, org_id)
        assert org is not None
        assert org.plan_type == "business"
        assert org.plan_status == "active"
        assert org.stripe_customer_id == "cus_business_1"
        assert org.stripe_subscription_id == "sub_business_1"
        assert org.stripe_price_id == "price_business_monthly"
        assert org.stripe_price_lookup_key == "business_monthly_gbp"
        assert org.current_period_end == datetime.fromtimestamp(
            1_800_000_000,
            tz=timezone.utc,
        ).replace(tzinfo=None)

        reference = db.execute(select(BillingCustomerReference)).scalars().first()
        assert reference is not None
        assert reference.org_id == org_id
        assert reference.external_customer_id == "cus_business_1"

        subscription = db.execute(select(Subscription)).scalars().first()
        assert subscription is not None
        assert subscription.org_id == org_id
        assert subscription.external_subscription_id == "sub_business_1"
        assert subscription.external_customer_id == "cus_business_1"
        assert subscription.plan_name == "business"
        assert subscription.status == "active"
        assert subscription.is_current is True


@pytest.mark.parametrize(
    ("event_type", "status_value", "event_id"),
    [
        ("customer.subscription.updated", "past_due", "evt_past_due"),
        ("customer.subscription.updated", "unpaid", "evt_unpaid"),
        ("customer.subscription.deleted", "canceled", "evt_canceled"),
    ],
)
def test_restricted_subscription_status_downgrades_org(
    stripe_test_client,
    monkeypatch,
    event_type,
    status_value,
    event_id,
):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    org_id = create_org(
        session_factory,
        name=f"restricted-{status_value}",
        plan_type="business",
        plan_limit=5000,
        plan_status="active",
        stripe_customer_id="cus_restricted",
        stripe_subscription_id="sub_restricted",
    )

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": event_id,
            "type": event_type,
            "data": {
                "object": {
                    "id": "sub_restricted",
                    "customer": "cus_restricted",
                    "subscription": "sub_restricted",
                    "status": status_value,
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_business_monthly",
                                    "lookup_key": "business_monthly_gbp",
                                }
                            }
                        ]
                    },
                }
            },
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    with session_factory() as db:
        org = db.get(Organization, org_id)
        assert org is not None
        assert org.plan_type == "starter"
        assert org.plan_status == status_value
        assert org.stripe_customer_id == "cus_restricted"
        assert org.stripe_subscription_id == "sub_restricted"

        subscription = db.execute(select(Subscription)).scalars().first()
        assert subscription is not None
        assert subscription.org_id == org_id
        assert subscription.external_subscription_id == "sub_restricted"
        assert subscription.plan_name == "business"
        assert subscription.status == status_value


def test_invoice_paid_reconciles_existing_subscription_customer_truth(
    stripe_test_client,
    monkeypatch,
):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")
    org_id = create_org(
        session_factory,
        name="invoice-paid-org",
        stripe_customer_id="cus_invoice_paid",
        stripe_subscription_id="sub_invoice_paid",
    )

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": "evt_invoice_paid",
            "type": "invoice.paid",
            "data": {
                "object": {
                    "customer": "cus_invoice_paid",
                    "subscription": "sub_invoice_paid",
                    "customer_email": "billing@paid.test",
                    "lines": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_executive_yearly",
                                    "lookup_key": "executive_yearly_gbp",
                                }
                            }
                        ]
                    },
                }
            },
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    with session_factory() as db:
        org = db.get(Organization, org_id)
        assert org is not None
        assert org.plan_type == "executive"
        assert org.plan_status == "active"

        subscription = db.execute(select(Subscription)).scalars().first()
        assert subscription is not None
        assert subscription.org_id == org_id
        assert subscription.external_subscription_id == "sub_invoice_paid"
        assert subscription.plan_name == "executive"
        assert subscription.status == "active"

        reference = db.execute(select(BillingCustomerReference)).scalars().first()
        assert reference is not None
        assert reference.external_customer_id == "cus_invoice_paid"
        assert reference.billing_email == "billing@paid.test"


def test_missing_org_mapping_fails_closed_without_subscription_activation(
    stripe_test_client,
    monkeypatch,
):
    client, session_factory = stripe_test_client
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_test")

    monkeypatch.setattr(
        api.stripe.Webhook,
        "construct_event",
        lambda *args, **kwargs: {
            "id": "evt_missing_org_mapping",
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_missing_org",
                    "customer": "cus_missing_org",
                    "status": "active",
                    "items": {
                        "data": [
                            {
                                "price": {
                                    "id": "price_enterprise_monthly",
                                    "lookup_key": "enterprise_monthly_gbp",
                                }
                            }
                        ]
                    },
                }
            },
        },
    )

    response = client.post(
        "/stripe/webhook",
        data=b"{}",
        headers={"Stripe-Signature": "sig"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "unmatched"
    assert response.json()["matched_org_id"] is None

    with session_factory() as db:
        assert db.execute(select(Subscription)).scalars().all() == []
        event = db.execute(
            select(StripeWebhookEvent).where(
                StripeWebhookEvent.stripe_event_id == "evt_missing_org_mapping"
            )
        ).scalars().first()
        assert event is not None
        assert event.processing_status == "unmatched"
        assert event.org_id is None
        assert event.error == "No deterministic organization mapping found."


def test_analyzer_endpoint_still_works_when_entitlement_allows(
    stripe_test_client,
    monkeypatch,
):
    client, session_factory = stripe_test_client
    org_id = create_org(
        session_factory,
        name="entitled-org",
        plan_type="business",
        plan_limit=5000,
        plan_status="active",
    )
    with session_factory() as db:
        db.add(
            Subscription(
                org_id=org_id,
                provider="stripe",
                external_subscription_id=f"sub_{uuid.uuid4().hex}",
                external_customer_id=f"cus_{uuid.uuid4().hex}",
                plan_name="business",
                status="active",
                is_current=True,
                source="test",
            )
        )
        db.commit()

    api.app.dependency_overrides[api.get_api_key_ctx] = lambda: SimpleNamespace(
        org_id=org_id,
        user_id=None,
        id=None,
    )

    try:
        response = client.post(
            "/analyze",
            json={"text": "Either party may terminate this agreement without notice."},
        )
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200
    data = response.json()
    assert "risk_score" in data
    assert "severity" in data
    assert "flags" in data
