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
