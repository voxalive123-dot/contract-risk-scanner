# analyzer/tests/test_api_contract.py

from fastapi.testclient import TestClient
from api import app


client = TestClient(app)


def test_analyze_endpoint_contract():
    payload = {"text": "Either party may terminate this agreement without notice."}
    r = client.post("/analyze", json=payload)

    assert r.status_code == 200
    data = r.json()

    # Contract keys must exist
    assert set(data.keys()) == {"risk_score", "severity", "flags"}

    # Types and allowed values
    assert isinstance(data["risk_score"], int)
    assert data["severity"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(data["flags"], list)

    # Minimal semantic check
    assert "termination without notice" in data["flags"]
