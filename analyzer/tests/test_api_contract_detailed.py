import os
from fastapi.testclient import TestClient

from api import app

client = TestClient(app, headers={"X-API-Key": os.environ["TEST_API_KEY"]})


def test_analyze_detailed_endpoint_contract():
    payload = {"text": "Either party may terminate this agreement without notice."}
    r = client.post("/analyze_detailed", json=payload)

    assert r.status_code == 200
    data = r.json()

    # Must include existing keys + findings + meta
    assert set(data.keys()) == {"risk_score", "severity", "flags", "findings", "meta"}

    # Meta must include audit + normalization + density + scan + confidence fields

    assert {
    "ruleset_version",
    "max_possible_score",
    "normalized_score",
    "word_count",
    "risk_density_per_1000_words",
    "scan_char_limit",
    "scanned_chars",
    "confidence",
}.issubset(set(data["meta"].keys()))
    assert isinstance(data["findings"], list)

    # We expect at least one termination-related finding for this text
    assert any(
        (f.get("rule_id") == "termination_without_notice")
        or (str(f.get("title", "")).lower() == "termination without notice")
        for f in data["findings"]
    )


def test_analyze_detailed_endpoint_includes_jurisdiction_family_findings():
    payload = {
        "text": "This agreement is governed by the laws of California and the parties submit to the exclusive jurisdiction of the courts of California."
    }
    r = client.post("/analyze_detailed", json=payload)

    assert r.status_code == 200
    data = r.json()

    assert set(data.keys()) == {"risk_score", "severity", "flags", "findings", "meta"}
    assert data["meta"]["ruleset_version"] == "1.7.0"
    assert data["severity"] == "MEDIUM"
    assert data["risk_score"] >= 6
    assert data["meta"]["normalized_score"] >= 28
    assert any(f.get("category") == "jurisdiction" for f in data["findings"])
    assert any(
        f.get("rule_id")
        in {
            "governing_law_foreign_or_unfamiliar",
            "jurisdiction_exclusive_foreign_forum",
            "jurisdiction_non_exclusive_forum",
            "arbitration_forum_or_seat",
            "venue_burden_foreign_court",
        }
        for f in data["findings"]
    )
    assert all("foreign" not in flag for flag in data["flags"])
    assert any(
        f.get("matched_location") in {"California", "California courts"}
        for f in data["findings"]
    )


def test_analyze_detailed_endpoint_includes_cross_clause_findings():
    payload = {
        "text": (
            "This agreement shall renew automatically for successive periods of 12 months unless either party gives "
            "at least 30 days written notice of non-renewal. Upon renewal, the fees may increase at Supplier's discretion."
        )
    }
    r = client.post("/analyze_detailed", json=payload)

    assert r.status_code == 200
    data = r.json()

    assert any(
        f.get("rule_id") == "cross_renewal_price_lock_in"
        for f in data["findings"]
    )
    assert any(
        adjustment.get("rule_id") == "cross_renewal_price_lock_in"
        for adjustment in data["meta"]["score_adjustments"]
    )
