from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api
from account_auth import create_session_token, hash_password
from crud import create_scan
from db import Base
from models import InternalOperatorAction, Membership, Organization, OwnerEntitlementGrant, Scan, User


@pytest.fixture
def dashboard_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    db_path = tmp_path / "dual_dashboard.sqlite"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
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


def create_account(session_factory, *, email: str, role: str = "owner", org_name: str | None = None):
    with session_factory() as db:
        org = Organization(name=org_name or f"org-{uuid.uuid4()}", plan_type="starter", plan_status="active", plan_limit=5)
        db.add(org)
        db.commit()
        db.refresh(org)
        user = User(org_id=org.id, email=email, password_hash=hash_password("correct horse battery staple"), role=role, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(Membership(user_id=user.id, org_id=org.id, role=role, status="active"))
        db.commit()
        return {"org_id": org.id, "user_id": user.id, "email": email, "token": create_session_token(user)}


def add_scan(session_factory, *, org_id, user_id, request_id: str):
    with session_factory() as db:
        scan = create_scan(
            db=db,
            org_id=org_id,
            user_id=user_id,
            request_id=request_id,
            risk_score=55,
            risk_density=0.2,
            confidence=0.9,
            ruleset_version="test",
            source_title=request_id,
            severity="medium",
        )
        db.commit()
        return scan.id


def test_account_scan_detail_is_org_scoped(dashboard_client):
    client, session_factory, _monkeypatch = dashboard_client
    first = create_account(session_factory, email="first@example.test")
    second = create_account(session_factory, email="second@example.test")
    first_scan_id = add_scan(session_factory, org_id=first["org_id"], user_id=first["user_id"], request_id="first-scan")

    own = client.get(f"/account/scans/{first_scan_id}", headers={"Authorization": f"Bearer {first['token']}"})
    cross = client.get(f"/account/scans/{first_scan_id}", headers={"Authorization": f"Bearer {second['token']}"})

    assert own.status_code == 200
    assert cross.status_code == 404


def test_non_internal_user_cannot_access_command_centre_summary(dashboard_client, monkeypatch):
    client, session_factory, monkeypatch = dashboard_client
    customer = create_account(session_factory, email="customer@example.test")
    monkeypatch.setenv("INTERNAL_ADMIN_EMAILS", "ops@example.test")

    response = client.get("/internal/ops/summary", headers={"Authorization": f"Bearer {customer['token']}"})

    assert response.status_code == 403


def test_owner_user_action_is_audit_logged_and_suspended_user_is_restricted(dashboard_client):
    client, session_factory, monkeypatch = dashboard_client
    owner = create_account(session_factory, email="admin.dashboard@voxarisk.com", org_name="VoxaRisk Platform")
    target = create_account(session_factory, email="target@example.test")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    response = client.post(
        f"/internal/ops/users/{target['user_id']}/suspend",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"reason": "Support confirmed suspicious account activity"},
    )

    assert response.status_code == 200
    assert response.json()["account_status"] == "suspended"
    assert client.get("/account/me", headers={"Authorization": f"Bearer {target['token']}"}).status_code == 401
    with session_factory() as db:
        action = db.query(InternalOperatorAction).filter_by(action_type="user_suspend").one()
        user = db.get(User, target["user_id"])
        assert action.actor_user_id == owner["user_id"]
        assert action.target_id == str(target["user_id"])
        assert user.account_status == "suspended"


def test_tester_expiry_is_enforced_and_excluded_from_revenue(dashboard_client):
    client, session_factory, monkeypatch = dashboard_client
    owner = create_account(session_factory, email="admin.dashboard@voxarisk.com", org_name="VoxaRisk Platform")
    tester = create_account(session_factory, email="tester@example.test", role="member")
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "admin.dashboard@voxarisk.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    created = client.post(
        "/internal/ops/testers/create",
        headers={"Authorization": f"Bearer {owner['token']}"},
        json={"email": "tester@example.test", "granted_plan": "executive", "duration_days": 1, "reason": "Owner tester access"},
    )
    assert created.status_code == 200
    assert client.get("/account/me", headers={"Authorization": f"Bearer {tester['token']}"}).json()["entitlement"]["source"] == "owner_grant"

    with session_factory() as db:
        grant = db.query(OwnerEntitlementGrant).filter_by(user_id=tester["user_id"]).one()
        grant.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

    entitlement = client.get("/account/me", headers={"Authorization": f"Bearer {tester['token']}"}).json()["entitlement"]
    summary = client.get("/internal/ops/summary", headers={"Authorization": f"Bearer {owner['token']}"}).json()

    assert entitlement["source"] != "owner_grant"
    assert summary["revenue_summary"]["amount_paid_minor_units"] == 0


def test_account_closure_is_soft_and_retains_scan_records(dashboard_client):
    client, session_factory, _monkeypatch = dashboard_client
    account = create_account(session_factory, email="close@example.test")
    scan_id = add_scan(session_factory, org_id=account["org_id"], user_id=account["user_id"], request_id="retained-scan")

    response = client.post(
        "/account/closure-request",
        headers={"Authorization": f"Bearer {account['token']}"},
        json={"reason": "No longer need the service"},
    )

    assert response.status_code == 200
    with session_factory() as db:
        user = db.get(User, account["user_id"])
        scan = db.get(Scan, scan_id)
        action = db.query(InternalOperatorAction).filter_by(action_type="account_closure_requested").one()
        assert user.account_status == "closure_requested"
        assert user.is_active is False
        assert user.soft_deleted_at is None
        assert scan is not None
        assert action.target_id == str(account["user_id"])
