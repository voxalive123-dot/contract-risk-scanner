from __future__ import annotations

from sqlalchemy import select

from analyzer.tests.test_account_identity import account_client, create_account, login
from models import DecisionAuditLog, OrganizationRiskPolicyAudit, Scan


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_account(client, account) -> str:
    return login(client, email=account["email"], password=account["password"]).json()["access_token"]


def _scan(client, token: str, text: str, **context):
    body = {"text": text, "source_title": context.pop("source_title", "Decision scan")}
    body.update(context)
    response = client.post("/account/analyze_detailed", headers=_auth(token), json=body)
    assert response.status_code == 200
    return response.json()


def test_default_policy_is_created_and_unknown_policy_is_reported(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    policy_response = client.get("/account/policy", headers=_auth(token))
    assert policy_response.status_code == 200
    policy = policy_response.json()["policy"]
    assert policy["broad_indemnity"] == "unknown"
    assert policy["data_use"] == "unknown"

    result = _scan(client, token, "Customer shall indemnify Supplier for any and all claims.")
    indemnity = next(f for f in result["findings"] if f.get("policy_category") == "broad_indemnity")
    assert indemnity["policy_status"] == "policy_unknown"
    assert result["findings"]


def test_policy_update_is_audited_and_broad_indemnity_conflicts(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    update = client.put(
        "/account/policy",
        headers=_auth(token),
        json={"policy": {"broad_indemnity": "allow_if_capped"}, "note": "Require caps."},
    )
    assert update.status_code == 200
    assert update.json()["policy"]["broad_indemnity"] == "allow_if_capped"

    with session_factory() as db:
        audit = db.execute(select(OrganizationRiskPolicyAudit)).scalars().one()
        assert audit.org_id == account["org_id"]
        assert audit.policy_key == "broad_indemnity"
        assert audit.old_value == "unknown"
        assert audit.new_value == "allow_if_capped"

    result = _scan(client, token, "Customer shall indemnify Supplier for any and all claims.")
    indemnity = next(f for f in result["findings"] if f.get("policy_category") == "broad_indemnity")
    assert indemnity["policy_status"] == "conflicts_with_policy"
    assert "unless capped" in indemnity["policy_explanation"]
    assert any(f.get("matched_text") for f in result["findings"])


def test_policy_mapping_for_data_auto_renewal_and_price_increase(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)
    response = client.put(
        "/account/policy",
        headers=_auth(token),
        json={
            "policy": {
                "data_use": "no_ai_training",
                "auto_renewal": "require_notice",
                "unilateral_price_increase": "reject",
            }
        },
    )
    assert response.status_code == 200

    result = _scan(
        client,
        token,
        (
            "Supplier may use customer data for any purpose including AI training and service improvement. "
            "This agreement automatically renews for successive one year terms. "
            "Supplier may increase fees at its sole discretion."
        ),
        user_role="buyer",
        contract_type="saas",
    )
    statuses = {finding.get("policy_category"): finding.get("policy_status") for finding in result["findings"]}
    assert statuses["data_use"] == "exceeds_tolerance"
    assert statuses["auto_renewal"] == "conflicts_with_policy"
    assert statuses["unilateral_price_increase"] == "exceeds_tolerance"
    assert len(result["findings"]) >= 3


def test_scan_and_finding_decisions_notes_and_cross_org_block(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    _scan(first_token and client, first_token, "Customer shall indemnify Supplier for any and all claims.")
    scan_id = client.get("/account/scans", headers=_auth(first_token)).json()["scans"][0]["id"]
    detail = client.get(f"/account/scans/{scan_id}", headers=_auth(first_token))
    assert detail.status_code == 200
    assert detail.json()["decision_state"]["state"] == "pending"
    finding_id = detail.json()["top_findings"][0]["rule_id"]
    assert detail.json()["finding_decisions"][0]["status"] == "unresolved"

    scan_decision = client.patch(
        f"/account/scans/{scan_id}/decision",
        headers=_auth(first_token),
        json={"state": "escalated", "reason_code": "legal_review_required", "note": "Needs counsel view."},
    )
    assert scan_decision.status_code == 200
    assert scan_decision.json()["decision_state"]["state"] == "escalated"

    finding_decision = client.patch(
        f"/account/scans/{scan_id}/findings/{finding_id}/decision",
        headers=_auth(first_token),
        json={"status": "redlined", "reason_code": "corrected_in_redline", "note": "Narrowed indemnity."},
    )
    assert finding_decision.status_code == 200
    assert finding_decision.json()["finding_decision"]["status"] == "redlined"

    note = client.post(
        f"/account/scans/{scan_id}/decision-notes",
        headers=_auth(first_token),
        json={"note": "Commercial owner wants a cap.", "finding_id": finding_id, "reason_code": "procurement_policy"},
    )
    assert note.status_code == 200
    assert note.json()["decision_notes"][0]["finding_id"] == finding_id

    blocked = client.patch(
        f"/account/scans/{scan_id}/decision",
        headers=_auth(second_token),
        json={"state": "accepted"},
    )
    assert blocked.status_code == 404

    with session_factory() as db:
        audit_events = db.execute(select(DecisionAuditLog).where(DecisionAuditLog.org_id == first["org_id"])).scalars().all()
        assert {event.event_type for event in audit_events} >= {"scan_decision", "finding_decision", "decision_note"}
        assert any(event.previous_state == "pending" and event.new_state == "escalated" for event in audit_events)


def test_prior_outcome_influences_future_posture_safely(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    _scan(client, token, "Customer shall indemnify Supplier for any and all claims.", source_title="First")
    first_scan_id = client.get("/account/scans", headers=_auth(token)).json()["scans"][0]["id"]
    client.patch(
        f"/account/scans/{first_scan_id}/decision",
        headers=_auth(token),
        json={"state": "escalated", "reason_code": "legal_review_required"},
    )

    second = _scan(client, token, "Customer shall indemnify Supplier for any and all claims.", source_title="Second")
    posture = second["meta"]["decision_intelligence"]["decision_posture"]
    assert "escalated this type of risk in prior contracts" in posture
    assert "not legal advice" in second["meta"]["decision_intelligence"]["boundary_notice"]


def test_decision_dashboard_is_org_scoped_and_aggregate_disabled(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    client.put(
        "/account/policy",
        headers=_auth(first_token),
        json={"policy": {"broad_indemnity": "escalate"}},
    )
    _scan(client, first_token, "Customer shall indemnify Supplier for any and all claims.", contract_type="services")
    first_scan_id = client.get("/account/scans", headers=_auth(first_token)).json()["scans"][0]["id"]
    client.patch(f"/account/scans/{first_scan_id}/decision", headers=_auth(first_token), json={"state": "rejected"})
    _scan(client, second_token, "This agreement includes unlimited liability.", source_title="Other org")

    dashboard = client.get("/account/decision-intelligence", headers=_auth(first_token))
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["decision_ratios"]["rejected"] > 0
    assert body["unresolved_finding_count"] >= 1
    assert body["most_common_policy_breaches"][0]["policy_category"] == "broad_indemnity"
    assert all(scan["organization_id"] == str(first["org_id"]) for scan in body["scans_with_open_decisions"])
    assert body["aggregate_insights_governance"]["aggregate_insights_enabled"] is False
    assert body["aggregate_insights_governance"]["customer_contract_text_excluded"] is True

    with session_factory() as db:
        scans = db.execute(select(Scan).where(Scan.org_id == first["org_id"])).scalars().all()
        assert scans[0].decision_intelligence_snapshot
        assert "policy_status_summary" in scans[0].decision_intelligence_snapshot
