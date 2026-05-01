from __future__ import annotations

import uuid

from sqlalchemy import select

from analyzer.scorer import score_contract
from analyzer.tests.test_account_identity import account_client, create_account, login
from models import Scan


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_account(client, account) -> str:
    return login(client, email=account["email"], password=account["password"]).json()["access_token"]


def test_saved_scan_persists_org_context_and_snapshots(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    response = client.post(
        "/account/analyze_detailed",
        headers=_auth(token),
        json={
            "text": (
                "Customer shall make an upfront payment before delivery. "
                "Supplier may suspend services immediately for disputed sums."
            ),
            "source_title": "Supplier services draft",
            "source_type": "text",
            "user_role": "buyer",
            "contract_type": "services",
            "counterparty_profile": "key_supplier",
            "value_criticality": "business_critical",
            "document_position": "vendor_paper",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["context_confidence"] == "high"

    with session_factory() as db:
        scan = db.execute(select(Scan).where(Scan.org_id == account["org_id"])).scalars().one()
        assert scan.org_id == account["org_id"]
        assert scan.user_id == account["user_id"]
        assert scan.source_title == "Supplier services draft"
        assert scan.source_type == "text"
        assert scan.severity == body["severity"]
        assert "suspension" in scan.clause_families_detected
        assert "upfront_payment_suspension" in scan.synthesis_patterns_triggered
        assert "business_critical" in scan.context_profile_snapshot
        assert scan.report_export_state == "absent"


def test_previous_scans_are_listed_only_for_current_organisation_and_detail_reopens(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    first_response = client.post(
        "/account/analyze_detailed",
        headers=_auth(first_token),
        json={"text": "Supplier may terminate for convenience at any time. Prepaid fees are non-refundable.", "source_title": "First org scan"},
    )
    second_response = client.post(
        "/account/analyze_detailed",
        headers=_auth(second_token),
        json={"text": "This agreement includes unlimited liability.", "source_title": "Second org scan"},
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200

    first_list = client.get("/account/scans", headers=_auth(first_token))
    assert first_list.status_code == 200
    scans = first_list.json()["scans"]
    assert len(scans) == 1
    assert scans[0]["source_title"] == "First org scan"
    assert scans[0]["organization_id"] == str(first["org_id"])
    assert "termination" in scans[0]["clause_families_detected"]
    assert first_list.json()["recurring_clause_families"]

    detail = client.get(f"/account/scans/{scans[0]['id']}", headers=_auth(first_token))
    assert detail.status_code == 200
    assert detail.json()["top_findings"]
    assert detail.json()["report_export_state"] == "absent"

    with session_factory() as db:
        second_scan_id = db.execute(select(Scan.id).where(Scan.org_id == second["org_id"])).scalar_one()

    blocked = client.get(f"/account/scans/{second_scan_id}", headers=_auth(first_token))
    assert blocked.status_code == 404


def test_scan_notes_are_organisation_scoped(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    client.post(
        "/account/analyze_detailed",
        headers=_auth(first_token),
        json={"text": "This agreement includes unlimited liability.", "source_title": "Note target"},
    )
    scan_id = client.get("/account/scans", headers=_auth(first_token)).json()["scans"][0]["id"]

    note = client.post(
        f"/account/scans/{scan_id}/notes",
        headers=_auth(first_token),
        json={"note": "Ask finance to confirm insurance coverage.", "finding_rule_id": "liability_unlimited"},
    )
    assert note.status_code == 200
    assert note.json()["note"]["finding_rule_id"] == "liability_unlimited"

    detail = client.get(f"/account/scans/{scan_id}", headers=_auth(first_token))
    assert detail.status_code == 200
    assert detail.json()["notes"][0]["note"] == "Ask finance to confirm insurance coverage."
    assert detail.json()["notes"][0]["created_by"] == str(first["user_id"])

    cross_org_note = client.post(
        f"/account/scans/{scan_id}/notes",
        headers=_auth(second_token),
        json={"note": "Should not attach."},
    )
    assert cross_org_note.status_code == 404


def test_context_defaults_and_confidence_levels_are_safe():
    missing = score_contract("This agreement includes unlimited liability.", include_findings=True, include_meta=True)
    partial = score_contract(
        "This agreement includes unlimited liability.",
        include_findings=True,
        include_meta=True,
        user_role="supplier",
        contract_type="services",
    )
    rich = score_contract(
        "This agreement includes unlimited liability.",
        include_findings=True,
        include_meta=True,
        user_role="supplier",
        contract_type="services",
        counterparty_profile="larger_counterparty",
        value_criticality="high_value",
        document_position="negotiated_draft",
    )

    assert missing["meta"]["context_confidence"] == "low"
    assert "Context not provided; decision posture is conservative." in missing["meta"]["context_limitations"]
    assert partial["meta"]["context_confidence"] == "medium"
    assert rich["meta"]["context_confidence"] == "high"


def test_context_framing_changes_emphasis_without_hiding_evidence():
    buyer = score_contract(
        "Customer shall make an upfront payment before delivery. Supplier may suspend services immediately for disputed sums.",
        include_findings=True,
        include_meta=True,
        user_role="buyer",
        contract_type="services",
        value_criticality="business_critical",
    )
    supplier = score_contract(
        "Supplier accepts unlimited liability and shall indemnify Customer for any and all claims.",
        include_findings=True,
        include_meta=True,
        user_role="supplier",
        contract_type="services",
        value_criticality="high_value",
    )
    low_value = score_contract(
        "Supplier may terminate for convenience at any time. Prepaid fees are non-refundable.",
        include_findings=True,
        include_meta=True,
        value_criticality="one_off",
    )

    assert buyer["findings"]
    assert any("Buyer context" in str(finding.get("contextual_emphasis", "")) for finding in buyer["findings"])
    assert any("Criticality posture" in note for note in buyer["meta"]["context_emphasis"])

    assert supplier["findings"]
    assert any("Supplier context" in str(finding.get("contextual_emphasis", "")) for finding in supplier["findings"])

    assert low_value["findings"]
    assert any("Limited-criticality context" in str(finding.get("contextual_emphasis", "")) for finding in low_value["findings"])
    assert any(finding.get("matched_text") for finding in low_value["findings"])
