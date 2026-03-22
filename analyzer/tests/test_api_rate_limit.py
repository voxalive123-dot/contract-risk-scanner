import os
import api
from fastapi.testclient import TestClient

client = TestClient(api.app, headers={"X-API-Key": os.environ["TEST_API_KEY"]})


def test_rate_limit_trips_when_capacity_low(monkeypatch):
    # Explicitly enable limiter for this test only
    monkeypatch.setattr(api, "RATE_LIMIT_ENABLED", True)

    # Deterministic: allow only 2 tokens, no refill.
    monkeypatch.setattr(api, "RATE_LIMIT_CAPACITY", 2)
    monkeypatch.setattr(api, "RATE_LIMIT_REFILL_PER_SEC", 0.0)

    api._BUCKETS.clear()

    payload = {"text": "Jurisdiction is England and Wales."}

    r1 = client.post("/analyze", json=payload)
    assert r1.status_code == 200

    r2 = client.post("/analyze", json=payload)
    assert r2.status_code == 200

    r3 = client.post("/analyze", json=payload)
    assert r3.status_code == 429