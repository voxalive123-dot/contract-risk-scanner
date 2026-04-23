from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api
import billing_portal
from account_auth import create_session_token, hash_password
from db import Base
from models import BillingCustomerReference, Membership, Organization, Subscription, User


@pytest.fixture
def billing_portal_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_portal")
    db_path = tmp_path / "account_billing_portal.sqlite"
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


def create_account(
    session_factory,
    *,
    membership_status: str | None = "active",
    add_billing_reference: bool = True,
    subscription_status: str | None = "active",
):
    raw_password = "correct horse battery staple"
    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type="starter",
            plan_status="active",
            plan_limit=5,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        user = User(
            org_id=org.id,
            email=f"portal-{uuid.uuid4()}@example.test",
            password_hash=hash_password(raw_password),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if membership_status is not None:
            db.add(
                Membership(
                    user_id=user.id,
                    org_id=org.id,
                    role="owner",
                    status=membership_status,
                )
            )

        if add_billing_reference:
            db.add(
                BillingCustomerReference(
                    org_id=org.id,
                    provider="stripe",
                    external_customer_id=f"cus_{uuid.uuid4().hex}",
                    billing_email=user.email,
                )
            )

        if subscription_status:
            db.add(
                Subscription(
                    org_id=org.id,
                    provider="stripe",
                    external_subscription_id=f"sub_{uuid.uuid4().hex}",
                    external_customer_id=f"cus_{uuid.uuid4().hex}",
                    plan_name="business",
                    status=subscription_status,
                    is_current=True,
                    source="test",
                )
            )

        token = create_session_token(user)
        db.commit()
        return {
            "email": user.email,
            "password": raw_password,
            "token": token,
            "org_id": org.id,
            "user_id": user.id,
        }


def login(client: TestClient, *, email: str, password: str) -> str:
    response = client.post("/account/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_authenticated_eligible_account_can_launch_billing_portal(
    billing_portal_client,
    monkeypatch,
):
    client, session_factory = billing_portal_client
    account = create_account(session_factory)
    token = login(client, email=account["email"], password=account["password"])
    calls = []

    def fake_create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(url="https://billing.stripe.test/session/123")

    monkeypatch.setattr(billing_portal.stripe.billing_portal.Session, "create", fake_create)

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {token}"},
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "url": "https://billing.stripe.test/session/123",
        "organization_id": str(account["org_id"]),
    }
    assert calls == [
        {
            "customer": calls[0]["customer"],
            "return_url": "https://voxarisk.test/account",
        }
    ]
    assert calls[0]["customer"].startswith("cus_")


def test_billing_portal_requires_authenticated_account(billing_portal_client):
    client, _session_factory = billing_portal_client

    response = client.post(
        "/account/billing/portal",
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing account session"


def test_missing_billing_customer_reference_fails_safely(billing_portal_client, monkeypatch):
    client, session_factory = billing_portal_client
    account = create_account(session_factory, add_billing_reference=False)

    def fail_if_called(**_kwargs):
        raise AssertionError("Stripe portal should not be called without customer reference")

    monkeypatch.setattr(billing_portal.stripe.billing_portal.Session, "create", fail_if_called)

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {account['token']}"},
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Billing portal is not available for this organisation"


def test_inactive_membership_denies_billing_portal_before_provider_call(billing_portal_client, monkeypatch):
    client, session_factory = billing_portal_client
    account = create_account(session_factory, membership_status="suspended")

    def fail_if_called(**_kwargs):
        raise AssertionError("Stripe portal should not be called for inactive membership")

    monkeypatch.setattr(billing_portal.stripe.billing_portal.Session, "create", fail_if_called)

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {account['token']}"},
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account membership is not valid"


def test_ambiguous_membership_denies_billing_portal(billing_portal_client, monkeypatch):
    client, session_factory = billing_portal_client
    account = create_account(session_factory)
    with session_factory() as db:
        second_org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type="starter",
            plan_status="active",
            plan_limit=5,
        )
        db.add(second_org)
        db.commit()
        db.refresh(second_org)
        db.add(
            Membership(
                user_id=account["user_id"],
                org_id=second_org.id,
                role="member",
                status="active",
            )
        )
        db.commit()

    def fail_if_called(**_kwargs):
        raise AssertionError("Stripe portal should not be called for ambiguous membership")

    monkeypatch.setattr(billing_portal.stripe.billing_portal.Session, "create", fail_if_called)

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {account['token']}"},
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account membership is not valid"


def test_missing_stripe_secret_fails_safely_before_provider_call(
    billing_portal_client,
    monkeypatch,
):
    client, session_factory = billing_portal_client
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    account = create_account(session_factory)

    def fail_if_called(**_kwargs):
        raise AssertionError("Stripe portal should not be called without secret")

    monkeypatch.setattr(billing_portal.stripe.billing_portal.Session, "create", fail_if_called)

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {account['token']}"},
        json={"return_url": "https://voxarisk.test/account"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Billing portal configuration is not available"


def test_billing_portal_linkage_does_not_alter_entitlement(billing_portal_client, monkeypatch):
    client, session_factory = billing_portal_client
    account = create_account(session_factory, subscription_status="active")
    token = login(client, email=account["email"], password=account["password"])
    before = client.get("/account/me", headers={"Authorization": f"Bearer {token}"}).json()["entitlement"]

    monkeypatch.setattr(
        billing_portal.stripe.billing_portal.Session,
        "create",
        lambda **_kwargs: SimpleNamespace(url="https://billing.stripe.test/session/456"),
    )

    response = client.post(
        "/account/billing/portal",
        headers={"Authorization": f"Bearer {token}"},
        json={"return_url": "https://voxarisk.test/account"},
    )
    after = client.get("/account/me", headers={"Authorization": f"Bearer {token}"}).json()["entitlement"]

    assert response.status_code == 200
    assert before == after
    assert after["source"] == "subscription"
    assert after["effective_plan"] == "business"