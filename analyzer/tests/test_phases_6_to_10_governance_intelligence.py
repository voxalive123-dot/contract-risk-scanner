from __future__ import annotations

from analyzer.tests.test_account_identity import account_client, create_account, login


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_account(client, account) -> str:
    return login(client, email=account["email"], password=account["password"]).json()["access_token"]


def _scan(client, token: str, text: str, **context):
    body = {"text": text, "source_title": context.pop("source_title", "Governance scan")}
    body.update(context)
    response = client.post("/account/analyze_detailed", headers=_auth(token), json=body)
    assert response.status_code == 200
    return response.json()


def test_contract_memory_detects_recurring_counterparty_without_overwriting_findings(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)
    text = "Customer shall indemnify Supplier for any and all claims."

    first = _scan(client, token, text, source_title="Acme services", counterparty_name="Acme Ltd")
    second = _scan(client, token, text, source_title="Acme renewal", counterparty_name="Acme Ltd")

    memory = second["meta"]["contract_memory"]
    assert memory["recurring_counterparty"]["detected"] is True
    assert memory["recurring_counterparty"]["prior_scan_count"] == 1
    assert memory["recurring_risky_clauses"]
    assert first["findings"][0]["matched_text"] == second["findings"][0]["matched_text"]


def test_contract_memory_is_org_scoped_and_no_history_is_safe(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    _scan(client, first_token, "This agreement includes unlimited liability.", counterparty_name="Shared Vendor")
    isolated = _scan(client, second_token, "This agreement includes unlimited liability.", counterparty_name="Shared Vendor")

    memory = isolated["meta"]["contract_memory"]
    assert memory["recurring_counterparty"]["prior_scan_count"] == 0
    assert memory["recurring_counterparty"]["detected"] is False
    assert memory["historical_clause_comparison"]["current_families"]


def test_outcome_event_tracking_can_be_stored_and_retrieved(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)
    _scan(client, token, "Supplier may terminate for convenience at any time.", source_title="Outcome target")
    scan_id = client.get("/account/scans", headers=_auth(token)).json()["scans"][0]["id"]

    created = client.post(
        f"/account/scans/{scan_id}/outcomes",
        headers=_auth(token),
        json={"event_category": "dispute", "note": "Supplier dispute arose after signature."},
    )
    assert created.status_code == 200
    assert created.json()["outcome_event"]["event_category"] == "dispute"

    listed = client.get(f"/account/scans/{scan_id}/outcomes", headers=_auth(token))
    detail = client.get(f"/account/scans/{scan_id}", headers=_auth(token))
    assert listed.json()["outcome_events"][0]["event_category"] == "dispute"
    assert detail.json()["outcome_events"][0]["note"] == "Supplier dispute arose after signature."


def test_executive_governance_dashboard_is_org_scoped_and_aggregates_portfolio_signals(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    _scan(
        client,
        first_token,
        "This agreement includes unlimited liability. This agreement automatically renews for successive one year terms.",
        source_title="Vendor A",
        counterparty_name="Vendor A",
        contract_type="saas",
        industry="saas",
        jurisdiction="uk",
    )
    _scan(client, second_token, "This agreement includes unlimited liability.", source_title="Other org", counterparty_name="Vendor A")

    dashboard = client.get("/account/decision-intelligence", headers=_auth(first_token))
    assert dashboard.status_code == 200
    portfolio = dashboard.json()["portfolio_governance"]
    assert portfolio["risk_concentration"]
    assert portfolio["risky_counterparties"][0]["counterparty"] == "vendor a"
    assert any(item["jurisdiction"] == "uk" for item in portfolio["jurisdiction_concentration"])
    assert portfolio["renewal_cliffs"]
    assert "Early intelligence" in portfolio["dataset_note"]

    unauthorized = client.get("/account/decision-intelligence")
    assert unauthorized.status_code in {401, 403}


def test_negotiation_intelligence_is_bounded_and_ai_cannot_override_it(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    high = _scan(
        client,
        token,
        "Customer shall indemnify Supplier for any and all claims. Supplier may suspend services immediately for disputed sums.",
        risk_posture="conservative",
        negotiation_leverage="low",
    )
    low = _scan(client, token, "This agreement starts on Monday.")

    negotiation = high["meta"]["negotiation_intelligence"]
    assert negotiation["priorities"]
    assert negotiation["minimum_acceptable_controls"]
    assert "not legal drafting advice" in negotiation["boundary"]
    assert low["meta"]["negotiation_intelligence"]["priorities"] == []

    ai_override = client.post(
        "/account/ai/explain",
        headers=_auth(token),
        json={
            "findings": [],
            "risk_score": 1,
            "severity": "low",
            "negotiation_intelligence": {"priorities": [{"priority": "force_override"}]},
        },
    )
    assert ai_override.status_code == 422


def test_sector_and_jurisdiction_intelligence_are_context_bound(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    saas = _scan(
        client,
        token,
        "Provider may use customer data for any purpose including AI training.",
        contract_type="saas",
        industry="saas",
        data_sensitivity="high",
    )
    healthcare = _scan(
        client,
        token,
        "Provider may use customer data for any purpose.",
        industry="healthcare",
        data_sensitivity="special_category",
    )
    real_estate = _scan(client, token, "Tenant shall pay rent monthly.", contract_type="lease", industry="real_estate")
    no_jurisdiction = _scan(client, token, "This agreement starts on Monday.")

    assert any(note["signal"] == "SaaS/data-sensitive review attention" for note in saas["meta"]["sector_jurisdiction_intelligence"]["notes"])
    assert any("healthcare" in note["signal"] for note in healthcare["meta"]["sector_jurisdiction_intelligence"]["notes"])
    assert any(note["signal"] == "Real-estate/lease relevance" for note in real_estate["meta"]["sector_jurisdiction_intelligence"]["notes"])
    assert not any(note["type"] == "jurisdiction" for note in no_jurisdiction["meta"]["sector_jurisdiction_intelligence"]["notes"])


def test_multi_document_grouping_and_conflict_signals_are_org_scoped(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    _scan(
        client,
        first_token,
        "Liability shall be limited to the fees paid in the previous 12 months.",
        source_title="MSA",
        contract_set_id="set-100",
        document_relationship_type="msa",
    )
    sla = _scan(
        client,
        first_token,
        "Supplier shall provide service levels and may suspend services immediately for disputed sums.",
        source_title="SLA",
        contract_set_id="set-100",
        document_relationship_type="sla",
    )
    _scan(
        client,
        second_token,
        "Liability shall be limited to the fees paid in the previous 12 months.",
        source_title="Other MSA",
        contract_set_id="set-100",
        document_relationship_type="msa",
    )

    linked = sla["meta"]["linked_document_intelligence"]
    assert linked["contract_set_detected"] is True
    assert linked["related_scan_count"] == 1
    assert linked["conflict_signals"][0]["type"] == "sla_liability_tension"

    contract_set = client.get("/account/contract-sets/set-100", headers=_auth(first_token))
    assert contract_set.status_code == 200
    assert contract_set.json()["scan_count"] == 2
    assert all(item["source_title"] != "Other MSA" for item in contract_set.json()["scans"])


def test_single_document_scan_remains_unaffected_without_contract_set(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    result = _scan(client, token, "This agreement includes unlimited liability.")

    linked = result["meta"]["linked_document_intelligence"]
    assert linked["contract_set_detected"] is False
    assert linked["conflict_signals"] == []
    assert result["findings"]
