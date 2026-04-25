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
    AccountPasswordToken,
    BillingCustomerReference,
    Membership,
    MonitoringSignal,
    Organization,
    OrganizationInvite,
    OwnerEntitlementGrant,
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


def create_user_org(
    session_factory,
    *,
    email: str,
    role: str = "owner",
    subscription: bool = False,
    org_name: str | None = None,
):
    with session_factory() as db:
        org = Organization(
            name=org_name or f"org-{uuid.uuid4()}",
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
    assert response.json()["overview"]["total_organizations"] == 1
    assert len(response.json()["organizations"]) == 1



def test_platform_owner_email_grants_internal_ops_without_admin_list(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(session_factory, email="admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )

    assert response.status_code == 200
    assert response.json()["read_only"] is True


def test_internal_ops_marks_canonical_and_legacy_platform_orgs(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    owner = create_user_org(
        session_factory,
        email="admin.dashboard@voxarisk.com",
        org_name="VoxaRisk Platform",
    )
    with session_factory() as db:
        legacy_org = Organization(
            name="voxarisk-platform-org",
            plan_type="starter",
            plan_status="active",
            plan_limit=5,
        )
        db.add(legacy_org)
        db.commit()
        db.refresh(legacy_org)

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )

    assert response.status_code == 200
    summaries = {item["name"]: item for item in response.json()["organizations"]}
    assert summaries["VoxaRisk Platform"]["platform_context"]["status"] == "canonical_platform_org"
    assert summaries["VoxaRisk Platform"]["platform_context"]["canonical_org_name"] == "VoxaRisk Platform"
    assert summaries["voxarisk-platform-org"]["platform_context"]["status"] == "legacy_platform_org"
    assert summaries["voxarisk-platform-org"]["platform_context"]["canonical_org_name"] == "VoxaRisk Platform"


def test_old_gmail_owner_identity_no_longer_grants_internal_ops(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    old_owner = create_user_org(session_factory, email="voxalive123@gmail.com", role="owner")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "admin.dashboard@voxarisk.com")

    response = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {old_owner['token']}"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Internal operations access denied: signed-in email is not configured as platform owner or internal admin"
    )


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
    body = response.json()
    assert body["overview"]["total_organizations"] == 1
    assert body["overview"]["total_accounts"] == 1
    assert body["overview"]["total_memberships"] == 1
    org = body["organizations"][0]
    assert org["effective_entitlement"]["source"] == "subscription"
    assert org["effective_entitlement"]["effective_plan"] == "business"
    assert org["plan_limit"] == 5
    assert org["account_count"] == 1
    assert org["subscription"]["status"] == "active"
    assert org["billing_customer_reference"]["external_customer_id"].startswith("cus_")
    assert org["status_badge"]["tone"] == "success"


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
    assert "manual_override_organization" in body["manual_controls"]
    assert body["accounts"][0]["email"] == "internal@example.test"
    assert body["effective_entitlement"]["effective_plan"] == "business"
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


def test_internal_owner_can_create_access_grant_for_existing_user(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(
        session_factory,
        email="admin.dashboard@voxarisk.com",
        org_name="VoxaRisk Platform",
    )
    target = create_user_org(session_factory, email="tester@example.test", role="member")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    response = client.post(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={
            "email": "tester@example.test",
            "granted_plan": "executive",
            "duration_days": 10,
            "reason": "family_beta_testing",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "granted_existing_account"
    assert body["setup_token"] is None
    assert body["grant"]["email"] == "tester@example.test"
    assert body["grant"]["granted_plan"] == "executive"

    account = client.get("/account/me", headers={"Authorization": f"Bearer {target['token']}"})
    assert account.status_code == 200
    assert account.json()["entitlement"]["source"] == "owner_grant"
    assert account.json()["entitlement"]["effective_plan"] == "executive"

    with session_factory() as db:
        grants = db.query(OwnerEntitlementGrant).all()
        assert len(grants) == 1
        assert grants[0].user_id == target["user_id"]
        assert grants[0].status == "active"


def test_non_owner_cannot_create_access_grant(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    customer = create_user_org(session_factory, email="customer@example.test", role="owner")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    response = client.post(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {customer['token']}"},
        json={
            "email": "tester@example.test",
            "granted_plan": "executive",
            "duration_days": 10,
            "reason": "family_beta_testing",
        },
    )

    assert response.status_code == 403


def test_unknown_email_creates_setup_flow_and_grant(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(
        session_factory,
        email="admin.dashboard@voxarisk.com",
        org_name="VoxaRisk Platform",
    )
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    response = client.post(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={
            "email": "new-beta@example.test",
            "granted_plan": "enterprise",
            "duration_days": 30,
            "reason": "family_beta_testing",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "needs_account_setup"
    assert isinstance(body["setup_token"], str)
    assert body["grant"]["granted_plan"] == "enterprise"
    assert body["grant"]["organization_name"] == "VoxaRisk Platform"

    with session_factory() as db:
        created_user = db.query(User).filter_by(email="new-beta@example.test").one()
        membership = db.query(Membership).filter_by(user_id=created_user.id, status="active").one()
        grant = db.query(OwnerEntitlementGrant).filter_by(user_id=created_user.id, status="active").one()
        token = db.query(AccountPasswordToken).filter_by(user_id=created_user.id, purpose="setup").one()
        assert membership.role == "member"
        assert grant.granted_plan == "enterprise"
        assert token.used_at is None


def test_internal_access_grants_list_and_revoke_work(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(
        session_factory,
        email="admin.dashboard@voxarisk.com",
        org_name="VoxaRisk Platform",
    )
    target = create_user_org(session_factory, email="grantee@example.test", role="member")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    created = client.post(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={
            "email": "grantee@example.test",
            "granted_plan": "enterprise",
            "duration_days": 30,
            "reason": "family_beta_testing",
        },
    )
    assert created.status_code == 200
    grant_id = created.json()["grant"]["id"]

    listed = client.get(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )
    assert listed.status_code == 200
    assert len(listed.json()["grants"]) == 1
    assert listed.json()["grants"][0]["email"] == "grantee@example.test"

    revoked = client.post(
        f"/internal/ops/access-grants/{grant_id}/revoke",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"reason": "Testing window complete"},
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "grant_revoked"
    assert revoked.json()["grant"]["status"] == "revoked"

    account = client.get("/account/me", headers={"Authorization": f"Bearer {target['token']}"})
    assert account.status_code == 200
    assert account.json()["entitlement"]["source"] != "owner_grant"

    relisted = client.get(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
    )
    assert relisted.status_code == 200
    assert relisted.json()["grants"] == []


def test_access_grants_endpoints_require_internal_auth(internal_ops_client):
    client, session_factory, monkeypatch = internal_ops_client
    owner = create_user_org(
        session_factory,
        email="admin.dashboard@voxarisk.com",
        org_name="VoxaRisk Platform",
    )
    target = create_user_org(session_factory, email="tester@example.test", role="member")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    grant = client.post(
        "/internal/ops/access-grants",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={
            "email": "tester@example.test",
            "granted_plan": "executive",
            "duration_days": 10,
            "reason": "family_beta_testing",
        },
    )
    assert grant.status_code == 200
    grant_id = grant.json()["grant"]["id"]

    listed = client.get("/internal/ops/access-grants")
    created = client.post(
        "/internal/ops/access-grants",
        json={
            "email": "tester@example.test",
            "granted_plan": "executive",
            "duration_days": 10,
            "reason": "family_beta_testing",
        },
    )
    revoked = client.post(
        f"/internal/ops/access-grants/{grant_id}/revoke",
        headers={"Authorization": f"Bearer {target['token']}"},
        json={"reason": "Trying to revoke without internal access"},
    )

    assert listed.status_code == 401
    assert created.status_code == 401
    assert revoked.status_code == 403
