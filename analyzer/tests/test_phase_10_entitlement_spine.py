from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import api
from auth_keys import hash_api_key
from db import Base
from entitlement_spine import resolve_entitlement_for_org
from models import ApiKey, Organization, Subscription


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


def create_org(session_factory, *, plan_type: str = "starter", plan_status: str = "active"):
    with session_factory() as db:
        org = Organization(
            name=f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status=plan_status,
            plan_limit=5,
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


def test_legacy_organization_paid_fields_are_not_primary_entitlement_authority(phase_10_client):
    _client, session_factory = phase_10_client
    org_id = create_org(session_factory, plan_type="enterprise", plan_status="active")

    entitlement = resolve_for(session_factory, org_id)

    assert entitlement.source == "no_current_subscription"
    assert entitlement.subscription_state == "no_subscription"
    assert entitlement.effective_plan == "starter"
    assert entitlement.paid_access is False
    assert entitlement.ai_review_notes_allowed is False


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
