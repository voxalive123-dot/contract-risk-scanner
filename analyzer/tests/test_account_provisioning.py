from __future__ import annotations

import uuid
import logging
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import api
from account_auth import InvalidCredentialsError, authenticate_user
from account_provisioning import (
    AccountTokenError,
    complete_password_token,
    provision_customer_account,
    request_password_reset,
    utcnow,
)
from db import Base
from entitlement_spine import resolve_entitlement_for_org
from models import AccountPasswordToken, Membership, Organization, Subscription, User


@pytest.fixture
def provisioning_client(tmp_path, monkeypatch):
    monkeypatch.setenv("ACCOUNT_SESSION_SECRET", "test-account-session-secret")
    db_path = tmp_path / "account_provisioning.sqlite"
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


def create_org(session_factory, *, plan_type: str = "starter"):
    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status="active",
            plan_limit=1000,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org.id


def used_tokens(session_factory) -> int:
    with session_factory() as db:
        return len(
            list(
                db.execute(
                    select(AccountPasswordToken).where(AccountPasswordToken.used_at.is_not(None))
                ).scalars()
            )
        )


def token_rows(session_factory) -> list[AccountPasswordToken]:
    with session_factory() as db:
        return list(db.execute(select(AccountPasswordToken)).scalars().all())


def test_controlled_account_provisioning_creates_identity_membership_and_setup_token_only(provisioning_client):
    _client, session_factory = provisioning_client
    org_id = create_org(session_factory)

    with session_factory() as db:
        provisioned = provision_customer_account(
            db,
            org_id=org_id,
            email="customer@example.test",
        )
        entitlement = resolve_entitlement_for_org(db, provisioned.organization)

        assert provisioned.user.email == "customer@example.test"
        assert provisioned.membership.status == "active"
        assert provisioned.setup_token
        assert db.execute(select(Subscription)).scalars().first() is None
        assert entitlement.effective_plan == "starter"
        assert entitlement.paid_access is False
        assert entitlement.ai_review_notes_allowed is False

    rows = token_rows(session_factory)
    assert len(rows) == 1
    assert rows[0].purpose == "setup"
    assert rows[0].token_hash != provisioned.setup_token


def test_password_setup_success_sets_password_marks_token_used_and_returns_starter_context(provisioning_client):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="setup@example.test",
        ).setup_token

    response = client.post(
        "/account/password/setup",
        json={"token": setup_token, "password": "new secure password"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["account"]["user"]["email"] == "setup@example.test"
    assert body["account"]["entitlement"]["effective_plan"] == "starter"
    assert body["account"]["entitlement"]["paid_access"] is False
    assert used_tokens(session_factory) == 1

    with session_factory() as db:
        context = authenticate_user(
            db,
            email="setup@example.test",
            password="new secure password",
        )
        assert str(context.organization.id) == str(org_id)


def test_used_setup_token_fails_closed(provisioning_client):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="used@example.test",
        ).setup_token

    first = client.post(
        "/account/password/setup",
        json={"token": setup_token, "password": "first password value"},
    )
    second = client.post(
        "/account/password/setup",
        json={"token": setup_token, "password": "second password value"},
    )

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == "Password setup token is invalid or expired"


def test_expired_token_fails_closed(provisioning_client):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="expired@example.test",
        ).setup_token
        row = db.execute(select(AccountPasswordToken)).scalars().first()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/account/password/setup",
        json={"token": setup_token, "password": "expired password"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Password setup token is invalid or expired"


def test_reset_request_endpoint_does_not_return_token_or_reveal_delivery_state(provisioning_client, caplog):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        provision_customer_account(db, org_id=org_id, email="reset-request@example.test")

    caplog.set_level(logging.INFO, logger="voxarisk.api")
    known = client.post(
        "/account/password/reset/request",
        json={"email": "reset-request@example.test"},
    )
    unknown = client.post(
        "/account/password/reset/request",
        json={"email": "missing@example.test"},
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert unknown.json() == {"status": "reset_requested"}
    assert known.json() == {"status": "reset_requested"}
    assert "token" not in known.text.lower()
    log_events = [record.__dict__.get("event") for record in caplog.records]
    assert "password_reset_delivery_failed" in log_events
    assert "password_reset_request_no_match" in log_events


def test_reset_request_sends_email_and_reset_link_completes_password_change(
    provisioning_client,
    monkeypatch,
    caplog,
):
    client, session_factory = provisioning_client
    sent_messages = []
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="email-reset@example.test",
        ).setup_token
        complete_password_token(
            db,
            raw_token=setup_token,
            password="original password",
            purpose="setup",
        )

    def fake_send_password_reset_email(*, to_email: str, reset_url: str) -> str:
        sent_messages.append({"to_email": to_email, "reset_url": reset_url})
        return "test"

    monkeypatch.setattr(api, "send_password_reset_email", fake_send_password_reset_email)
    monkeypatch.setattr(api, "password_reset_url", lambda token: f"https://voxarisk.test/reset-password?token={token}")

    caplog.set_level(logging.INFO, logger="voxarisk.api")
    response = client.post(
        "/account/password/reset/request",
        json={"email": "email-reset@example.test"},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "reset_requested"}
    assert len(sent_messages) == 1
    assert sent_messages[0]["to_email"] == "email-reset@example.test"
    log_events = [record.__dict__.get("event") for record in caplog.records]
    assert "password_reset_token_created" in log_events
    assert "password_reset_delivery_started" in log_events
    assert "password_reset_delivery_succeeded" in log_events
    reset_token = parse_qs(urlparse(sent_messages[0]["reset_url"]).query)["token"][0]

    reset = client.post(
        "/account/password/reset/complete",
        json={"token": reset_token, "password": "updated password"},
    )
    assert reset.status_code == 200

    with session_factory() as db:
        with pytest.raises(InvalidCredentialsError):
            authenticate_user(db, email="email-reset@example.test", password="original password")
        context = authenticate_user(db, email="email-reset@example.test", password="updated password")
        assert str(context.organization.id) == str(org_id)

    reused = client.post(
        "/account/password/reset/complete",
        json={"token": reset_token, "password": "another updated password"},
    )
    assert reused.status_code == 400


def test_password_reset_completion_changes_password_without_widening_entitlement(provisioning_client):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory, plan_type="enterprise")
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="reset@example.test",
        ).setup_token
        complete_password_token(
            db,
            raw_token=setup_token,
            password="original password",
            purpose="setup",
        )
        reset_token = request_password_reset(db, email="reset@example.test")

    response = client.post(
        "/account/password/reset/complete",
        json={"token": reset_token, "password": "updated password"},
    )

    assert response.status_code == 200
    entitlement = response.json()["account"]["entitlement"]
    assert entitlement["effective_plan"] == "starter"
    assert entitlement["paid_access"] is False
    assert entitlement["ai_review_notes_allowed"] is False

    with session_factory() as db:
        context = authenticate_user(db, email="reset@example.test", password="updated password")
        assert str(context.organization.id) == str(org_id)
        assert context.entitlement.effective_plan == "starter"


def test_password_reset_completion_logs_invalid_reasons(provisioning_client, caplog):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="expired-reset@example.test",
        ).setup_token
        complete_password_token(
            db,
            raw_token=setup_token,
            password="original password",
            purpose="setup",
        )
        expired_token = request_password_reset(db, email="expired-reset@example.test")
        row = db.execute(
            select(AccountPasswordToken).where(
                AccountPasswordToken.token_hash.is_not(None),
                AccountPasswordToken.purpose == "reset",
            )
        ).scalars().first()
        row.expires_at = utcnow() - timedelta(minutes=1)
        db.commit()

    caplog.set_level(logging.INFO, logger="voxarisk.api")
    expired = client.post(
        "/account/password/reset/complete",
        json={"token": expired_token, "password": "updated password"},
    )
    not_found = client.post(
        "/account/password/reset/complete",
        json={"token": "not-a-real-token", "password": "updated password"},
    )
    short_password = client.post(
        "/account/password/reset/complete",
        json={"token": "not-a-real-token", "password": "short"},
    )
    missing_token = client.post(
        "/account/password/reset/complete",
        json={"password": "updated password"},
    )

    assert expired.status_code == 400
    assert not_found.status_code == 400
    assert short_password.status_code == 400
    assert missing_token.status_code == 400
    reasons = [record.__dict__.get("reason") for record in caplog.records]
    assert "token_expired" in reasons
    assert "token_not_found" in reasons
    assert "password_validation_failed" in reasons
    assert "missing_token" in reasons


def test_inactive_membership_blocks_setup_completion(provisioning_client):
    _client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        provisioned = provision_customer_account(
            db,
            org_id=org_id,
            email="inactive@example.test",
        )
        membership = db.get(Membership, provisioned.membership.id)
        membership.status = "suspended"
        db.commit()

        with pytest.raises(AccountTokenError):
            complete_password_token(
                db,
                raw_token=provisioned.setup_token,
                password="inactive password",
                purpose="setup",
            )


def test_missing_membership_blocks_reset_request(provisioning_client):
    _client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        provisioned = provision_customer_account(
            db,
            org_id=org_id,
            email="missing-membership@example.test",
        )
        db.delete(db.get(Membership, provisioned.membership.id))
        db.commit()

        reset_token = request_password_reset(db, email="missing-membership@example.test")

    assert reset_token is None


def test_authenticated_paid_behavior_after_setup_still_comes_from_subscription_truth(provisioning_client):
    client, session_factory = provisioning_client
    org_id = create_org(session_factory)
    with session_factory() as db:
        setup_token = provision_customer_account(
            db,
            org_id=org_id,
            email="paid@example.test",
        ).setup_token
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

    response = client.post(
        "/account/password/setup",
        json={"token": setup_token, "password": "paid account password"},
    )

    assert response.status_code == 200
    entitlement = response.json()["account"]["entitlement"]
    assert entitlement["source"] == "subscription"
    assert entitlement["effective_plan"] == "business"
    assert entitlement["paid_access"] is True
    assert entitlement["ai_review_notes_allowed"] is True
