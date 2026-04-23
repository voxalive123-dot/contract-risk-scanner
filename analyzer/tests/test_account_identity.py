from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api
from account_auth import hash_password
from auth_keys import hash_api_key
from db import Base
from models import ApiKey, Membership, Organization, Subscription, User


@pytest.fixture
def account_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    db_path = tmp_path / "account_identity.sqlite"
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
    plan_name: str = "starter",
    subscription_status: str | None = None,
    membership_status: str = "active",
    email: str | None = None,
):
    raw_password = "correct horse battery staple"
    raw_key = f"vxrk-account-{uuid.uuid4()}"

    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type=plan_name,
            plan_status=subscription_status or "active",
            plan_limit=1000,
        )
        db.add(org)
        db.commit()
        db.refresh(org)

        user = User(
            org_id=org.id,
            email=email or f"user-{uuid.uuid4()}@example.test",
            password_hash=hash_password(raw_password),
            role="owner",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        if membership_status:
            db.add(
                Membership(
                    user_id=user.id,
                    org_id=org.id,
                    role="owner",
                    status=membership_status,
                )
            )

        if subscription_status:
            db.add(
                Subscription(
                    org_id=org.id,
                    provider="stripe",
                    external_subscription_id=f"sub_{uuid.uuid4().hex}",
                    external_customer_id=f"cus_{uuid.uuid4().hex}",
                    plan_name=plan_name,
                    status=subscription_status,
                    is_current=True,
                    source="test",
                )
            )

        db.add(
            ApiKey(
                org_id=org.id,
                user_id=user.id,
                name="account-test-key",
                key_hash=hash_api_key(raw_key),
                active=True,
            )
        )
        db.commit()
        return {
            "email": user.email,
            "password": raw_password,
            "org_id": org.id,
            "api_key": raw_key,
        }


def login(client: TestClient, *, email: str, password: str):
    return client.post(
        "/account/login",
        json={"email": email, "password": password},
    )


def test_successful_login_returns_account_context(account_client):
    client, session_factory = account_client
    account = create_account(session_factory)

    response = login(client, email=account["email"], password=account["password"])

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["account"]["user"]["email"] == account["email"]
    assert body["account"]["organization"]["id"] == str(account["org_id"])
    assert body["account"]["membership"]["status"] == "active"


def test_account_me_requires_authentication(account_client):
    client, _session_factory = account_client

    response = client.get("/account/me")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing account session"


def test_authenticated_user_is_linked_to_membership_org(account_client):
    client, session_factory = account_client
    account = create_account(session_factory)
    token = login(client, email=account["email"], password=account["password"]).json()["access_token"]

    response = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["organization"]["id"] == str(account["org_id"])
    assert body["membership"]["role"] == "owner"


def test_authenticated_starter_org_remains_non_premium(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="starter")
    token = login(client, email=account["email"], password=account["password"]).json()["access_token"]

    response = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    entitlement = response.json()["entitlement"]
    assert entitlement["effective_plan"] == "starter"
    assert entitlement["paid_access"] is False
    assert entitlement["ai_review_notes_allowed"] is False


def test_authenticated_paid_org_gets_premium_only_from_resolver_subscription(account_client):
    client, session_factory = account_client
    account = create_account(
        session_factory,
        plan_name="business",
        subscription_status="active",
    )
    token = login(client, email=account["email"], password=account["password"]).json()["access_token"]

    response = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    entitlement = response.json()["entitlement"]
    assert entitlement["source"] == "subscription"
    assert entitlement["effective_plan"] == "business"
    assert entitlement["paid_access"] is True
    assert entitlement["ai_review_notes_allowed"] is True


def test_legacy_paid_user_without_subscription_remains_starter_safe(account_client):
    client, session_factory = account_client
    account = create_account(
        session_factory,
        plan_name="enterprise",
        subscription_status=None,
    )
    token = login(client, email=account["email"], password=account["password"]).json()["access_token"]

    response = client.get(
        "/account/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    entitlement = response.json()["entitlement"]
    assert entitlement["effective_plan"] == "starter"
    assert entitlement["paid_access"] is False
    assert entitlement["ai_review_notes_allowed"] is False


def test_missing_membership_fails_closed(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, membership_status="")

    response = login(client, email=account["email"], password=account["password"])

    assert response.status_code == 403
    assert response.json()["detail"] == "Account membership is not valid"


def test_inactive_membership_fails_closed(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, membership_status="suspended")

    response = login(client, email=account["email"], password=account["password"])

    assert response.status_code == 403
    assert response.json()["detail"] == "Account membership is not valid"


def test_existing_analyze_and_ai_gating_stay_resolver_backed(account_client, monkeypatch):
    client, session_factory = account_client
    account = create_account(
        session_factory,
        plan_name="business",
        subscription_status="active",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        api,
        "generate_ai_explanation",
        lambda *args, **kwargs: SimpleNamespace(
            model_dump=lambda mode="json": {
                "status": "available",
                "model": "test-model",
                "ai_summary": {
                    "overview": "The deterministic scan surfaced a commercial issue.",
                    "risk_posture_summary": "Review before acceptance.",
                    "negotiation_focus": ["Clarify the termination position."],
                    "evidence_notes": [],
                    "uncertainty_notes": [],
                    "boundary_notice": "This is not legal advice, legal opinion, contract approval, or a guarantee.",
                },
            }
        ),
    )

    analyze_response = client.post(
        "/analyze",
        headers={"X-API-Key": account["api_key"]},
        json={"text": "Either party may terminate this agreement without notice."},
    )
    ai_response = client.post(
        "/ai/explain",
        headers={"X-API-Key": account["api_key"]},
        json={
            "risk_score": 9,
            "severity": "MEDIUM",
            "flags": ["termination without notice"],
            "findings": [
                {
                    "rule_id": "termination_without_notice",
                    "title": "Termination without notice",
                    "category": "termination",
                    "severity": 3,
                    "rationale": "Counterparty exit rights may be too broad.",
                    "matched_text": "Either party may terminate this agreement without notice.",
                }
            ],
            "meta": {
                "confidence": 0.9,
                "top_risks": [],
                "matched_rule_count": 1,
                "suppressed_rule_count": 0,
                "contradiction_count": 0,
            },
        },
    )

    assert analyze_response.status_code == 200
    assert set(analyze_response.json().keys()) == {"risk_score", "severity", "flags"}
    assert ai_response.status_code == 200
    assert ai_response.json()["status"] == "available"
