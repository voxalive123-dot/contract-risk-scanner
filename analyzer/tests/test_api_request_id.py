import os
from fastapi.testclient import TestClient

from api import app, REQUEST_ID_HEADER

client = TestClient(app, headers={"X-API-Key": os.environ["TEST_API_KEY"]})


def test_request_id_header_present():
    r = client.post("/analyze", json={"text": "Jurisdiction is England and Wales."})
    assert r.status_code == 200
    assert REQUEST_ID_HEADER in r.headers
    assert len(r.headers[REQUEST_ID_HEADER]) > 10


def test_request_id_echoes_if_provided():
    rid = "test-request-id-123"
    r = client.post(
        "/analyze",
        json={"text": "Jurisdiction is England and Wales."},
        headers={REQUEST_ID_HEADER: rid},
    )
    assert r.status_code == 200
    assert r.headers[REQUEST_ID_HEADER] == rid