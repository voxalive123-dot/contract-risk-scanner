from __future__ import annotations

import uuid
from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import api
from crud import month_start_utc
from db import Base
from models import Organization, Scan


@pytest.fixture
def quota_client(tmp_path):
    db_path = tmp_path / "quota_enforcement.sqlite"
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
    plan_limit: int = 1000,
    name: str | None = None,
):
    with session_factory() as db:
        org = Organization(
            name=name or f"org-{uuid.uuid4()}",
            plan_type=plan_type,
            plan_status=plan_status,
            plan_limit=plan_limit,
        )
        db.add(org)
        db.commit()
        db.refresh(org)
        return org.id


def create_scan_rows(session_factory, *, org_id, count: int):
    with session_factory() as db:
        month_start = month_start_utc()
        for index in range(count):
            db.add(
                Scan(
                    org_id=org_id,
                    user_id=None,
                    request_id=f"existing-{index}",
                    risk_score=10,
                    risk_density=1,
                    confidence=1,
                    ruleset_version="test",
                    scan_input_length=0,
                    created_at=month_start + timedelta(minutes=index),
                )
            )
        db.commit()


def override_api_key_ctx(org_id):
    return lambda: SimpleNamespace(org_id=org_id, user_id=None, id=None)


def test_starter_quota_allows_scans_under_limit(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    create_scan_rows(session_factory, org_id=org_id, count=4)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post(
            "/analyze",
            json={"text": "Either party may terminate this agreement without notice."},
        )
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200


def test_starter_quota_blocks_over_limit(quota_client, monkeypatch):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    create_scan_rows(session_factory, org_id=org_id, count=5)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    calls = {"score": 0}

    def score_should_not_run(*args, **kwargs):
        calls["score"] += 1
        raise AssertionError("score_contract should not run when quota is exceeded")

    monkeypatch.setattr(api, "score_contract", score_should_not_run)

    try:
        response = client.post(
            "/analyze",
            json={"text": "Either party may terminate this agreement without notice."},
        )
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 429
    assert response.json()["detail"] == {
        "error": "monthly_scan_quota_exceeded",
        "current_plan": "starter",
        "monthly_limit": 5,
        "scans_used": 5,
    }
    assert calls["score"] == 0

    with session_factory() as db:
        count = db.execute(select(Scan)).scalars().all()
        assert len(count) == 5


def test_active_business_uses_business_quota(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="business", plan_status="active")
    create_scan_rows(session_factory, org_id=org_id, count=99)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200


def test_active_executive_uses_executive_quota(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="executive", plan_status="trialing")
    create_scan_rows(session_factory, org_id=org_id, count=499)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200


def test_active_enterprise_uses_enterprise_quota(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="enterprise", plan_status="active")
    create_scan_rows(session_factory, org_id=org_id, count=1999)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200


@pytest.mark.parametrize("status_value", ["past_due", "unpaid", "canceled"])
def test_restricted_paid_org_falls_back_to_starter_safe_quota(quota_client, status_value):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="business", plan_status=status_value)
    create_scan_rows(session_factory, org_id=org_id, count=5)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 429
    assert response.json()["detail"]["current_plan"] == "starter"
    assert response.json()["detail"]["monthly_limit"] == 5


def test_unknown_plan_status_fails_safe(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="enterprise", plan_status="mystery_status")
    create_scan_rows(session_factory, org_id=org_id, count=5)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 429
    assert response.json()["detail"] == {
        "error": "monthly_scan_quota_exceeded",
        "current_plan": "starter",
        "monthly_limit": 5,
        "scans_used": 5,
    }


def test_analyzer_output_unchanged_when_under_quota(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)
    text = "Either party may terminate this agreement without notice."

    try:
        response = client.post("/analyze", json={"text": text})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 200
    scored = api.score_contract(text)
    assert response.json() == {
        "risk_score": int(scored["risk_score"]),
        "severity": str(scored["severity"]),
        "flags": list(scored["flags"]),
    }


def test_quota_check_happens_before_new_scan_is_recorded_when_blocked(quota_client):
    client, session_factory = quota_client
    org_id = create_org(session_factory, plan_type="starter", plan_status="active")
    create_scan_rows(session_factory, org_id=org_id, count=5)
    api.app.dependency_overrides[api.get_api_key_ctx] = override_api_key_ctx(org_id)

    try:
        response = client.post("/analyze_detailed", json={"text": "Jurisdiction is England and Wales."})
    finally:
        api.app.dependency_overrides.pop(api.get_api_key_ctx, None)

    assert response.status_code == 429

    with session_factory() as db:
        scans = db.execute(select(Scan)).scalars().all()
        assert len(scans) == 5
