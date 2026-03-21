import os
import uuid
from sqlalchemy import text
from db import engine

def test_analyze_writes_scan_and_usage_log(client):
    # Require the env var you already use for auth in your app.
    # If your code uses a different env var name, update this single line.
    raw_key = os.environ.get("TEST_API_KEY")
    assert raw_key, "Set TEST_API_KEY env var for this test run."

    # Pre-count
    with engine.begin() as conn:
        scans_before = conn.execute(text("SELECT COUNT(*) FROM scans")).scalar_one()
        logs_before = conn.execute(text("SELECT COUNT(*) FROM usage_logs")).scalar_one()

    req_id = f"test-{uuid.uuid4()}"
    r = client.post(
        "/analyze",
        json={"text": "This agreement includes unlimited liability."},
        headers={"X-API-Key": raw_key, "X-Request-ID": req_id},
    )
    assert r.status_code == 200

    # Post-count and request_id linkage
    with engine.begin() as conn:
        scans_after = conn.execute(text("SELECT COUNT(*) FROM scans")).scalar_one()
        logs_after = conn.execute(text("SELECT COUNT(*) FROM usage_logs")).scalar_one()

        # Verify at least one row with our request id exists in each table (request_id is nullable in schema)
        scan_match = conn.execute(
            text("SELECT COUNT(*) FROM scans WHERE request_id = :rid"),
            {"rid": req_id},
        ).scalar_one()
        log_match = conn.execute(
            text("SELECT COUNT(*) FROM usage_logs WHERE request_id = :rid AND endpoint = '/analyze' AND status_code = 200"),
            {"rid": req_id},
        ).scalar_one()

    assert scans_after == scans_before + 1
    assert logs_after == logs_before + 1
    # If your request_id middleware/header is optional, these can be 0; but for best product, we want linkage.
    assert scan_match == 1
    assert log_match == 1
