from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api
from account_auth import create_session_token, hash_password
from crud import create_scan, create_usage_log
from db import Base
from models import (
    BillingCustomerReference,
    Membership,
    MonitoringSignal,
    Organization,
    OrganizationInvite,
    Subscription,
    User,
)


@pytest.fixture
def internal_ops_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    db_path = tmp_path / "internal_ops.sqlite"
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
        yield client, SessionLocal, monkeypatch
    finally:
        api.app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def create_user_org(session_factory, *, email: str, role: str = "owner", subscription: bool = False):
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
            email=email,
            password_hash=hash_password("correct horse battery staple"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(Membership(user_id=user.id, org_id=org.id, role=role, status="active"))

        if subscription:
            db.add(
                BillingCustomerReference(
                    org_id=org.id,
                    provider="stripe",
                    external_customer_id=f"cus_{uuid.uuid4().hex}",
                    billing_email=email,
                )
            )
            db.add(
                Subscription(
                    org_id=org.id,
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
        return {"org_id": org.id, "user_id": user.id, "email": email, "token": create_session_token(user)}


def add_activity(session_factory, *, org_id, user_id):
    with session_factory() as db:
        create_scan(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id="req-internal-ops",
            risk_score=42,
            risk_density=0.1,
            confidence=0.8,
            ruleset_version="test",
        )
        create_usage_log(
            db=db,
            org_id=org_id,
            user_id=user_id,
            api_key_id=None,
            endpoint="/analyze",
            request_id="req-internal-ops",
            method="POST",
            ip="127.0.0.1",
            duration_ms=1,
            status_code=200,
        )
        db.add(
            MonitoringSignal(
                org_id=org_id,
                category="test",
                signal_type="internal_ops_test_signal",
                severity="warning",
                message="Test signal",
            )
        )
        db.add(
            OrganizationInvite(
                org_id=org_id,
                invited_email="pending@example.test",
                role="member",
                token_hash=f"hash-{uuid.uuid4()}",
                status="pending",
                invited_by_user_id=user_id,
                expires_at=datetime.now(timezone.utc),
            )
        )
        db.commit()


def test_internal_admin_access_allowed(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test")
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["read_only"] is True
    assert len(response.json()["organizations"]) == 1



def test_platform_owner_email_grants_internal_ops_without_admin_list(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(session_factory, email="voxalive123@gmail.com")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "voxalive123@gmail.com")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["read_only"] is True
def test_normal_customer_owner_denied_internal_ops(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    customer = create_user_org(session_factory, email="customer-owner@example.test", role="owner")
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {customer['token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Internal operations access denied: signed-in email is not configured as platform owner or internal admin"


def test_internal_ops_requires_configuration(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Internal operations access is not configured"


def test_organisations_and_entitlement_summaries_load(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )

    assert response.status_code == 200
    org = response.json()["organizations"][0]
    assert org["effective_entitlement"]["source"] == "subscription"
    assert org["effective_entitlement"]["effective_plan"] == "business"
    assert org["subscription"]["status"] == "active"
    assert org["billing_customer_reference"]["external_customer_id"].startswith("cus_")


def test_recent_usage_scans_invites_and_signals_visible(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    add_activity(session_factory, org_id=admin["org_id"], user_id=admin["user_id"])
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    response = client.get(
        f"/internal/ops/organizations/{admin['org_id']}",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is True
    assert body["manual_controls"] == []
    assert body["recent_scans"][0]["request_id"] == "req-internal-ops"
    assert body["recent_usage"][0]["endpoint"] == "/analyze"
    assert body["recent_invites"][0]["email"] == "pending@example.test"
    assert body["recent_signals"][0]["signal_type"] == "internal_ops_test_signal"


def test_internal_ops_does_not_mutate_entitlement(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    admin = create_user_org(session_factory, email="internal@example.test", subscription=True)
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "internal@example.test")

    before = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {admin['token']}"},
    ).json()["entitlement"]
    response = client.get(
        f"/internal/ops/organizations/{admin['org_id']}",
        headers={"Authorization": f"Bearer {admin['token']}"},
    )
    after = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {admin['token']}"},
    ).json()["entitlement"]

    assert response.status_code == 200
    assert before == after