from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import ai_explain
import api
from auth_keys import hash_api_key
from db import Base
from models import ApiKey, Organization


@pytest.fixture
def ai_test_client(tmp_path):
    db_path = tmp_path / "ai_explain.sqlite"
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


def create_org_and_key(
    session_factory,
    *,
    plan_type: str,
    plan_status: str,
    plan_limit: int = 1000,
):
    raw_key = f"vxrk-ai-{uuid.uuid4()}"

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

        api_key = ApiKey(
            org_id=org.id,
            user_id=None,
            name="ai-test-key",
            key_hash=hash_api_key(raw_key),
            active=True,
        )
        db.add(api_key)
        db.commit()

    return raw_key


def build_request(
    *,
    confidence: float = 0.92,
    source_type: str | None = "text",
    extraction_method: str | None = "direct",
    confidence_hint: float | None = None,
    has_extractable_text: bool | None = None,
    findings: list[dict] | None = None,
):
    return {
        "risk_score": 9,
        "severity": "MEDIUM",
        "flags": ["termination without notice"],
        "findings": findings
        if findings is not None
        else [
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
            "confidence": confidence,
            "top_risks": [
                {
                    "rule_id": "termination_without_notice",
                    "title": "Termination without notice",
                    "category": "termination",
                    "severity": 3,
                    "weight": 5,
                }
            ],
            "matched_rule_count": 1 if findings is None else len(findings),
            "suppressed_rule_count": 0,
            "contradiction_count": 0,
        },
        "source_type": source_type,
        "extraction_method": extraction_method,
        "confidence_hint": confidence_hint,
        "has_extractable_text": has_extractable_text,
    }


def build_provider_summary():
    return {
        "overview": "The deterministic scan surfaced a contract control issue that should be reviewed before acceptance.",
        "risk_posture_summary": "The current posture supports negotiation rather than passive acceptance.",
        "negotiation_focus": [
            "Tighten termination notice requirements.",
            "Balance exit rights before approval.",
        ],
        "evidence_notes": [
            {
                "rule_id": "termination_without_notice",
                "title": "Termination without notice",
                "explanation": "The deterministic finding indicates that exit rights may be too broad.",
                "evidence_excerpt": "terminate this agreement without notice",
            }
        ],
        "uncertainty_notes": [],
        "boundary_notice": "placeholder",
    }


def test_starter_plan_denied_ai_access(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="starter", plan_status="active")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == {
        "error": "ai_explain_not_available_for_plan",
        "current_plan": "starter",
        "feature": "ai_explain",
    }


def test_active_business_plan_allowed_and_provider_receives_only_deterministic_fields(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status="active")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    captured: dict[str, object] = {}

    def fake_call(payload, *, model, uncertainty_notes):
        captured["payload"] = payload
        captured["model"] = model
        captured["uncertainty_notes"] = uncertainty_notes
        return build_provider_summary()

    monkeypatch.setattr(ai_explain, "_call_openai_json", fake_call)

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "available"
    assert body["model"] == "gpt-4o-mini"
    assert set(captured["payload"].keys()) == {
        "risk_score",
        "severity",
        "flags",
        "findings",
        "meta",
        "source_type",
        "extraction_method",
        "confidence_hint",
        "has_extractable_text",
    }
    assert captured["payload"]["findings"][0]["matched_text"] == (
        "Either party may terminate this agreement without notice."
    )


@pytest.mark.parametrize("status_value", ["past_due", "canceled", "mystery_status"])
def test_restricted_or_unknown_plan_status_denied(ai_test_client, monkeypatch, status_value):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status=status_value)
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 403
    assert response.json()["detail"]["error"] == "ai_explain_not_available_for_plan"
    assert response.json()["detail"]["current_plan"] == "starter"


def test_missing_openai_api_key_returns_disabled_response(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status="active")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "disabled",
        "reason": "openai_api_key_not_configured",
    }


def test_provider_failure_returns_unavailable_response(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status="active")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def raise_provider_error(*args, **kwargs):
        raise ai_explain.AIProviderError("provider failure")

    monkeypatch.setattr(ai_explain, "_call_openai_json", raise_provider_error)

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "unavailable",
        "reason": "ai_provider_error",
    }


def test_ai_route_does_not_return_changed_deterministic_score_or_severity(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status="active")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_explain, "_call_openai_json", lambda *args, **kwargs: build_provider_summary())

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(),
    )

    assert response.status_code == 200
    body = response.json()
    assert "risk_score" not in body
    assert "severity" not in body
    assert "flags" not in body
    assert body["status"] == "available"


def test_low_confidence_or_sparse_findings_produce_uncertainty_notes(ai_test_client, monkeypatch):
    client, session_factory = ai_test_client
    raw_key = create_org_and_key(session_factory, plan_type="business", plan_status="active")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(ai_explain, "_call_openai_json", lambda *args, **kwargs: build_provider_summary())

    response = client.post(
        "/ai/explain",
        headers={"X-API-Key": raw_key},
        json=build_request(
            confidence=0.3,
            source_type="pdf",
            extraction_method="ocr",
            confidence_hint=0.45,
            has_extractable_text=False,
        ),
    )

    assert response.status_code == 200
    notes = response.json()["ai_summary"]["uncertainty_notes"]
    assert notes
    assert any("confidence" in note.lower() for note in notes)
    assert any(
        "few or no deterministic findings" in note.lower()
        or "small number of deterministic findings" in note.lower()
        for note in notes
    )
    assert any("extraction" in note.lower() or "ocr" in note.lower() for note in notes)
