import os

from fastapi.testclient import TestClient

from api import app, MAX_TEXT_CHARS

client = TestClient(app)


def test_analyze_rejects_empty_text():
    r = client.post("/analyze", json={"text": "   \n\t  "})
    assert r.status_code == 422
    data = r.json()
    assert "text" in str(data).lower()


def test_analyze_rejects_oversized_text():
    too_big = "A" * (MAX_TEXT_CHARS + 1)
    r = client.post("/analyze", json={"text": too_big})
    assert r.status_code == 422
    data = r.json()
    assert "maximum length" in str(data).lower()


def test_analyze_rejects_unsupported_context_value():
    r = client.post(
        "/analyze",
        json={
            "text": "Either party may terminate without notice.",
            "user_role": "wizard",
            "criticality_level": "mission_critical",
            "risk_posture": "balanced",
        },
    )
    assert r.status_code == 422
    assert "unsupported user_role" in str(r.json()).lower()


def test_analyze_accepts_phase_one_context_fields():
    r = client.post(
        "/analyze",
        headers={"X-API-Key": os.environ["TEST_API_KEY"]},
        json={
            "text": "Either party may terminate without notice.",
            "user_role": "customer",
            "contract_type": "saas",
            "criticality_level": "mission_critical",
            "risk_posture": "conservative",
            "deal_value": "250000",
            "industry": "fintech",
            "jurisdiction": "uk",
            "negotiation_leverage": "low",
            "counterparty_tier": "enterprise",
            "data_sensitivity": "high",
            "insurance_coverage": "confirmed",
        },
    )
    assert r.status_code == 200
