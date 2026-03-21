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