from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import api
from account_auth import create_session_token, hash_password
from db import Base
from models import Membership, Organization, OrganizationInvite, Subscription, User
from team_invites import utcnow


@pytest.fixture
def team_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    db_path = tmp_path / "team_invites.sqlite"
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


def create_account(session_factory, *, role: str = "owner", subscription_status: str | None = None):
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
            email=f"{role}-{uuid.uuid4()}@example.test",
            password_hash=hash_password("correct horse battery staple"),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.add(Membership(user_id=user.id, org_id=org.id, role=role, status="active"))

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
        db.commit()
        return {
            "org_id": org.id,
            "user_id": user.id,
            "email": user.email,
            "token": create_session_token(user),
        }


def create_invite(client: TestClient, token: str, *, email: str, role: str = "member"):
    return client.post(
        "/account/team/invites",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": email, "role": role},
    )


def accept_invite(client: TestClient, *, invite_token: str, email: str, password: str = "accepted password"):
    return client.post(
        "/account/team/invites/accept",
        json={"token": invite_token, "email": email, "password": password},
    )


def test_owner_can_create_valid_admin_invite(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")

    response = create_invite(
        client,
        owner["token"],
        email="admin-invite@example.test",
        role="admin",
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "invite_created"
    assert body["invite"]["email"] == "admin-invite@example.test"
    assert body["invite"]["role"] == "admin"
    assert body["invite_token"]
    assert "/team/accept?token=" in body["accept_url"]


def test_admin_can_create_member_invite(team_client):
    client, session_factory = team_client
    admin = create_account(session_factory, role="admin")

    response = create_invite(
        client,
        admin["token"],
        email="member-invite@example.test",
        role="member",
    )

    assert response.status_code == 200
    assert response.json()["invite"]["role"] == "member"


def test_admin_cannot_assign_admin_role(team_client):
    client, session_factory = team_client
    admin = create_account(session_factory, role="admin")

    response = create_invite(
        client,
        admin["token"],
        email="blocked-admin@example.test",
        role="admin",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account role cannot create this team invite"


def test_member_cannot_create_invite(team_client):
    client, session_factory = team_client
    member = create_account(session_factory, role="member")

    response = create_invite(
        client,
        member["token"],
        email="blocked@example.test",
        role="member",
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Account role cannot create this team invite"


def test_invite_acceptance_creates_active_membership_and_session(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")
    invited_email = "accepted@example.test"
    invite = create_invite(client, owner["token"], email=invited_email, role="member").json()

    response = accept_invite(client, invite_token=invite["invite_token"], email=invited_email)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["account"]["user"]["email"] == invited_email
    assert body["account"]["organization"]["id"] == str(owner["org_id"])
    assert body["account"]["membership"]["role"] == "member"
    assert body["account"]["entitlement"]["effective_plan"] == "starter"

    team = client.get("/account/team", headers={"Authorization": f"Bearer {owner['token']}"})
    assert team.status_code == 200
    assert {m["email"] for m in team.json()["memberships"]} >= {owner["email"], invited_email}


def test_used_invite_fails_safely(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")
    invited_email = "used@example.test"
    invite = create_invite(client, owner["token"], email=invited_email).json()

    first = accept_invite(client, invite_token=invite["invite_token"], email=invited_email)
    second = accept_invite(client, invite_token=invite["invite_token"], email=invited_email)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Team invite is invalid, expired, or cannot be accepted"


def test_expired_invite_fails_safely(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")
    invited_email = "expired@example.test"
    invite = create_invite(client, owner["token"], email=invited_email).json()
    with session_factory() as db:
        row = db.execute(select(OrganizationInvite)).scalars().first()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    response = accept_invite(client, invite_token=invite["invite_token"], email=invited_email)

    assert response.status_code == 400
    with session_factory() as db:
        row = db.execute(select(OrganizationInvite)).scalars().first()
        assert row.status == "expired"


def test_invalid_invite_email_fails_safely(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")
    invite = create_invite(client, owner["token"], email="right@example.test").json()

    response = accept_invite(client, invite_token=invite["invite_token"], email="wrong@example.test")

    assert response.status_code == 400


def test_duplicate_pending_invite_fails_safely(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")

    first = create_invite(client, owner["token"], email="duplicate@example.test")
    second = create_invite(client, owner["token"], email="duplicate@example.test")

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "A pending invite already exists for this email"


def test_existing_active_membership_blocks_invite_acceptance(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner")
    existing = create_account(session_factory, role="member")
    invite = create_invite(client, owner["token"], email=existing["email"]).json()

    response = accept_invite(client, invite_token=invite["invite_token"], email=existing["email"])

    assert response.status_code == 400
    assert response.json()["detail"] == "Team invite is invalid, expired, or cannot be accepted"


def test_team_member_premium_behavior_still_comes_from_org_subscription(team_client):
    client, session_factory = team_client
    owner = create_account(session_factory, role="owner", subscription_status="active")
    invited_email = "paid-member@example.test"
    invite = create_invite(client, owner["token"], email=invited_email, role="member").json()

    response = accept_invite(client, invite_token=invite["invite_token"], email=invited_email)

    assert response.status_code == 200
    entitlement = response.json()["account"]["entitlement"]
    assert entitlement["source"] == "subscription"
    assert entitlement["effective_plan"] == "business"
    assert entitlement["paid_access"] is True
    assert entitlement["ai_review_notes_allowed"] is True