from __future__ import annotations

from sqlalchemy import select

from account_auth import authenticate_user
from account_provisioning import complete_password_token
from analyzer.tests.test_account_provisioning import create_org, provisioning_client, token_rows
from bootstrap_platform_owner import bootstrap_platform_owner
from models import AccountPasswordToken, Membership, Organization, User


def test_platform_owner_bootstrap_creates_owner_account_membership_and_setup_token(provisioning_client, monkeypatch):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "voxalive123@gmail.com")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    with session_factory() as db:
        payload = bootstrap_platform_owner(db, org_id=str(org_id))

    assert payload["status"] == "owner_bootstrap_ready"
    assert payload["email"] == "voxalive123@gmail.com"
    assert payload["role"] == "owner"
    assert payload["setup_url"].startswith("http://localhost:3000/account/setup?token=")

    setup = client.post(
        "/account/password/setup",
        json={"token": payload["setup_token"], "password": "owner secure password"},
    )
    assert setup.status_code == 200
    bearer = setup.json()["access_token"]

    internal = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert internal.status_code == 200

    with session_factory() as db:
        context = authenticate_user(
            db,
            email="voxalive123@gmail.com",
            password="owner secure password",
        )
        assert str(context.organization.id) == str(org_id)
        assert context.membership.role == "owner"
        assert context.membership.status == "active"


def test_platform_owner_bootstrap_is_idempotent_and_invalidates_previous_setup_token(provisioning_client, monkeypatch):
    _client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "voxalive123@gmail.com")

    with session_factory() as db:
        first = bootstrap_platform_owner(db, org_id=str(org_id))
        second = bootstrap_platform_owner(db, org_id=str(org_id))

    assert first["email"] == second["email"] == "voxalive123@gmail.com"
    assert first["user_id"] == second["user_id"]
    assert first["membership_id"] == second["membership_id"]
    assert first["setup_token"] != second["setup_token"]

    rows = token_rows(session_factory)
    assert len(rows) == 2
    assert len([row for row in rows if row.used_at is not None]) == 1
    assert len([row for row in rows if row.used_at is None]) == 1

    with session_factory() as db:
        users = list(db.execute(select(User).where(User.email == "voxalive123@gmail.com")).scalars().all())
        memberships = list(db.execute(select(Membership).where(Membership.user_id == users[0].id)).scalars().all())
        assert len(users) == 1
        assert len(memberships) == 1
        assert memberships[0].org_id == org_id
        assert memberships[0].status == "active"

def test_platform_owner_bootstrap_can_create_deterministic_owner_org_and_set_password(provisioning_client, monkeypatch):
    client, session_factory = provisioning_client
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "voxalive123@gmail.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")
    monkeypatch.delenv("INTERNAL_ADMIN_EMAILS", raising=False)

    with session_factory() as db:
        payload = bootstrap_platform_owner(db, password="owner direct password")

    assert payload["status"] == "owner_bootstrap_ready"
    assert payload["credential_status"] == "password_set_directly"
    assert payload["setup_token"] is None
    assert payload["setup_url"] is None
    assert payload["signin_url"] == "/signin"
    assert payload["internal_operations_url"] == "/internal/operations"
    assert payload["org_name"] == "VoxaRisk Platform"

    signin = client.post(
        "/account/login",
        json={"email": "voxalive123@gmail.com", "password": "owner direct password"},
    )
    assert signin.status_code == 200
    bearer = signin.json()["access_token"]

    internal = client.get(
        "/internal/ops/organizations",
        headers={"Authorization": f"Bearer {bearer}"},
    )
    assert internal.status_code == 200

    with session_factory() as db:
        orgs = list(db.execute(select(Organization).where(Organization.name == "VoxaRisk Platform")).scalars().all())
        assert len(orgs) == 1
        setup_tokens = list(db.execute(select(AccountPasswordToken)).scalars().all())
        assert len(setup_tokens) == 1
        assert setup_tokens[0].used_at is not None


def test_platform_owner_bootstrap_reuses_named_owner_org_on_repeat_direct_password_runs(provisioning_client, monkeypatch):
    _client, session_factory = provisioning_client
    monkeypatch.setenv("PLATFORM_OWNER_EMAIL", "voxalive123@gmail.com")
    monkeypatch.setenv("PLATFORM_OWNER_ORG_NAME", "VoxaRisk Platform")

    with session_factory() as db:
        first = bootstrap_platform_owner(db, password="first owner password")
        second = bootstrap_platform_owner(db, password="second owner password")

    assert first["org_id"] == second["org_id"]
    assert first["user_id"] == second["user_id"]
    assert first["membership_id"] == second["membership_id"]
    assert second["credential_status"] == "password_set_directly"

    with session_factory() as db:
        orgs = list(db.execute(select(Organization).where(Organization.name == "VoxaRisk Platform")).scalars().all())
        users = list(db.execute(select(User).where(User.email == "voxalive123@gmail.com")).scalars().all())
        memberships = list(db.execute(select(Membership).where(Membership.user_id == users[0].id)).scalars().all())
        assert len(orgs) == 1
        assert len(users) == 1
        assert len(memberships) == 1
        assert memberships[0].status == "active"