from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import api
from auth_keys import hash_api_key
from db import Base
from entitlement_spine import resolve_entitlement_for_org
from models import ApiKey, Organization, OwnerEntitlementGrant, Subscription, User
from stripe_billing import PLAN_QUOTAS


@pytest.fixture
def phase_10_client(tmp_path):
    db_path = tmp_path / "phase_10_entitlement.sqlite"
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
    plan_type: str = "starter",
    plan_status: str = "active",
    plan_limit: int = 5,
):
    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status=plan_status,
            plan_limit=plan_limit,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org.id


def add_subscription(
    session_factory,
    *,
    org_id,
    plan_name: str,
    status: str,
    is_current: bool = True,
):
    with session_factory() as db:
        subscription = Subscription(
            org_id=org_id,
            provider="stripe",
            external_subscription_id=f"sub_{uuid.uuid4().hex}",
            external_customer_id=f"cus_{uuid.uuid4().hex}",
            plan_name=plan_name,
            status=status,
            is_current=is_current,
            source="test",
        )
        db.add(subscription)
        db.commit()


def add_api_key(session_factory, *, org_id) -> str:
    raw_key = f"vxrk-phase10-{uuid.uuid4()}"
    with session_factory() as db:
        api_key = ApiKey(
            org_id=org_id,
            user_id=None,
            name="phase-10-test-key",
            key_hash=hash_api_key(raw_key),
            active=True,
        )
        db.add(api_key)
        db.commit()
    return raw_key


def add_owner_grant(
    session_factory,
    *,
    org_id,
    granted_plan: str,
    expires_delta: timedelta | None,
    user_id=None,
    status: str = "active",
    scan_quota_override: int | None = None,
):
    with session_factory() as db:
        now = datetime.now(timezone.utc)
        owner_org = Organization(
            name=f"owner-org-{uuid.uuid4()}",
            plan_type="starter",
            plan_status="active",
            plan_limit=5,
        )
        db.add(owner_org)
        db.commit()
        db.refresh(owner_org)

        owner_user = User(
            org_id=owner_org.id,
            email=f"owner-{uuid.uuid4()}@example.test",
            password_hash="unused",
            role="owner",
            is_active=True,
        )
        db.add(owner_user)
        db.commit()
        db.refresh(owner_user)

        db.add(
            OwnerEntitlementGrant(
                org_id=org_id,
                user_id=user_id,
                granted_plan=granted_plan,
                grant_type="trial",
                scan_quota_override=scan_quota_override,
                reason="entitlement test",
                starts_at=now,
                expires_at=now + expires_delta if expires_delta is not None else None,
                status=status,
                created_by_user_id=owner_user.id,
            )
        )
        db.commit()


def resolve_for(session_factory, org_id):
    with session_factory() as db:
        org = db.get(Organization, org_id)
        return resolve_entitlement_for_org(db, org)


def test_entitlement_resolution_uses_current_persisted_subscription(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    add_subscription(session_factory, org_id=org_id, plan_name="business", status="active")

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "subscription"
    assert entitlement.subscription_state == "active"
    assert entitlement.effective_plan == "business"
    assert entitlement.monthly_scan_limit == 100
    assert entitlement.paid_access is True
    assert entitlement.ai_review_notes_allowed is True
    assert entitlement.fail_closed is False


def test_unknown_subscription_state_fails_closed_to_starter_safe(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    add_subscription(session_factory, org_id=org_id, plan_name="enterprise", status="unknown_state")

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.subscription_state == "restricted"
    assert entitlement.raw_subscription_state == "unknown_state"
    assert entitlement.effective_plan == "starter"
    assert entitlement.monthly_scan_limit == 5
    assert entitlement.paid_access is False
    assert entitlement.ai_review_notes_allowed is False
    assert entitlement.fail_closed is True
    assert entitlement.reason == "unknown_subscription_state"


@pytest.mark.parametrize(
    ("state", "paid_access"),
    [
        ("no_subscription", False),
        ("checkout_started", False),
        ("active", True),
        ("trialing", True),
        ("past_due", False),
        ("unpaid", False),
        ("canceled", False),
        ("incomplete", False),
        ("incomplete_expired", False),
        ("restricted", False),
        ("manual_override", True),
    ],
)
def test_entitlement_state_matrix_for_ai_gating(phase_10_client, state, paid_access):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    add_subscription(session_factory, org_id=org_id, plan_name="executive", status=state)

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.paid_access is paid_access
    assert entitlement.ai_review_notes_allowed is paid_access
    assert entitlement.effective_plan == ("executive" if paid_access else "starter")


def test_non_paid_plan_never_gets_ai_even_with_active_subscription(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    add_subscription(session_factory, org_id=org_id, plan_name="starter", status="active")

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.effective_plan == "starter"
    assert entitlement.paid_access is False
    assert entitlement.ai_review_notes_allowed is False


def test_active_enterprise_legacy_org_without_current_subscription_is_honoured(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(
        session_factory,
        plan_type="enterprise",
        plan_status="active",
        plan_limit=2000,
    )

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.subscription_state == "active"
    assert entitlement.effective_plan == "enterprise"
    assert entitlement.monthly_scan_limit == 2000
    assert entitlement.paid_access is True
    assert entitlement.ai_review_notes_allowed is True
    assert entitlement.reason == "legacy_organization_entitlement_honored"


def test_active_business_legacy_org_without_current_subscription_is_honoured(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(
        session_factory,
        plan_type="business",
        plan_status="active",
        plan_limit=250,
    )

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.subscription_state == "active"
    assert entitlement.effective_plan == "business"
    assert entitlement.monthly_scan_limit == 250
    assert entitlement.paid_access is True
    assert entitlement.ai_review_notes_allowed is True


def test_active_executive_owner_grant_gives_executive_access(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_owner_grant(session_factory, org_id=org_id, granted_plan="executive", expires_delta=timedelta(days=14))

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "owner_grant"
    assert entitlement.effective_plan == "executive"
    assert entitlement.monthly_scan_limit == PLAN_QUOTAS["executive"]
    assert entitlement.paid_access is True


def test_active_enterprise_owner_grant_gives_enterprise_access(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_owner_grant(
        session_factory,
        org_id=org_id,
        granted_plan="enterprise",
        expires_delta=timedelta(days=30),
        scan_quota_override=3500,
    )

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "owner_grant"
    assert entitlement.effective_plan == "enterprise"
    assert entitlement.monthly_scan_limit == 3500
    assert entitlement.paid_access is True


def test_expired_owner_grant_does_not_apply(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_owner_grant(session_factory, org_id=org_id, granted_plan="executive", expires_delta=timedelta(days=-1))

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.effective_plan == "starter"
    assert entitlement.paid_access is False


def test_revoked_owner_grant_does_not_apply(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_owner_grant(session_factory, org_id=org_id, granted_plan="executive", expires_delta=timedelta(days=14))

    with session_factory() as db:
        grant = db.execute(
            select(OwnerEntitlementGrant).where(OwnerEntitlementGrant.org_id == org_id)
        ).scalars().first()
        assert grant is not None
        grant.status = "revoked"
        grant.revoked_at = api.month_start_utc()
        grant.revocation_reason = "entitlement test revoke"
        db.commit()

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.effective_plan == "starter"
    assert entitlement.paid_access is False


def test_active_subscription_remains_source_of_truth_when_owner_grant_exists(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_subscription(session_factory, org_id=org_id, plan_name="business", status="active")
    add_owner_grant(session_factory, org_id=org_id, granted_plan="enterprise", expires_delta=timedelta(days=30))

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "subscription"
    assert entitlement.effective_plan == "business"


def test_unknown_owner_grant_state_does_not_unlock_paid_access(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=5)
    add_owner_grant(
        session_factory,
        org_id=org_id,
        granted_plan="enterprise",
        expires_delta=timedelta(days=30),
        status="mystery_state",
    )

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.effective_plan == "starter"
    assert entitlement.paid_access is False


def test_starter_legacy_org_without_current_subscription_remains_starter_safe(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active", plan_limit=999)

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "legacy_organization"
    assert entitlement.subscription_state == "active"
    assert entitlement.effective_plan == "starter"
    assert entitlement.monthly_scan_limit == 5
    assert entitlement.paid_access is False
    assert entitlement.ai_review_notes_allowed is False


def test_restricted_or_unknown_legacy_status_fails_closed(phase_10_client):
    _client, session_factory = phase_10_client
    restricted_org_id = create_org(session_factory, plan_type="enterprise", plan_status="canceled", plan_limit=2000)
    unknown_org_id = create_org(session_factory, plan_type="enterprise", plan_status="mystery_status", plan_limit=2000)

    restricted = resolve_for(session_factory, restricted_org_id)
    unknown = resolve_for(session_factory, unknown_org_id)

    assert restricted.source == "legacy_organization"
    assert restricted.effective_plan == "starter"
    assert restricted.paid_access is False
    assert restricted.ai_review_notes_allowed is False
    assert restricted.fail_closed is True

    assert unknown.source == "legacy_organization"
    assert unknown.subscription_state == "restricted"
    assert unknown.raw_subscription_state == "mystery_status"
    assert unknown.effective_plan == "starter"
    assert unknown.paid_access is False
    assert unknown.ai_review_notes_allowed is False
    assert unknown.fail_closed is True


def test_existing_analyze_endpoint_still_works_with_api_key_flow(phase_10_client):
    client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    raw_key = add_api_key(session_factory, org_id=org_id)

    response = client.post(
        "/analyze",
        headers={"X-API-Key": raw_key},
        json={"text": "Either party may terminate this agreement without notice."},
    )

    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"risk_score", "severity", "flags"}
    assert isinstance(body["risk_score"], int)
