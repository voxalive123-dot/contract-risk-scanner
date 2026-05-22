from __future__ import annotations

from sqlalchemy import select

from analyzer.scorer import score_contract
from analyzer.tests.test_account_identity import account_client, create_account, login
from models import OrganizationRiskPolicyAudit


def _rule(result, rule_id: str) -> dict:
    return next(finding for finding in result["findings"] if finding["rule_id"] == rule_id)


def _rules(result) -> set[str]:
    return {finding["rule_id"] for finding in result["findings"]}


def _patterns(result) -> set[str]:
    return set(result["meta"]["synthesis_patterns_triggered"])


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login_account(client, account) -> str:
    return login(client, email=account["email"], password=account["password"]).json()["access_token"]


def _scan(client, token: str, text: str, **context):
    body = {"text": text, "source_title": context.pop("source_title", "Decision intelligence scan")}
    body.update(context)
    response = client.post("/account/analyze_detailed", headers=_auth(token), json=body)
    assert response.status_code == 200
    return response.json()


def test_role_aware_buyer_and_seller_context_changes_contextual_impact():
    text = "Supplier may suspend services immediately for disputed invoices or unresolved payment issues."

    buyer = score_contract(text, include_findings=True, include_meta=True, user_role="buyer")
    seller = score_contract(text, include_findings=True, include_meta=True, user_role="seller")

    buyer_finding = _rule(buyer, "service_suspension_right")
    seller_finding = _rule(seller, "service_suspension_right")
    assert "Buyer-side context" in buyer_finding["contextual_impact"]
    assert "Seller-side context" in seller_finding["contextual_impact"]
    assert buyer_finding["matched_text"] == seller_finding["matched_text"]


def test_role_aware_sections_reflect_criticality_posture_missing_and_legacy_context():
    text = "Supplier may suspend services immediately for disputed invoices or unresolved payment issues."

    critical = score_contract(text, include_findings=True, include_meta=True, user_role="buyer", criticality_level="mission_critical")
    conservative = score_contract(text, include_findings=True, include_meta=True, user_role="buyer", risk_posture="conservative")
    missing = score_contract(text, include_findings=True, include_meta=True)
    legacy = score_contract(text, include_findings=True, include_meta=True, value_criticality="business_critical")

    assert "Mission-critical context increases operational exposure." in _rule(critical, "service_suspension_right")["operational_exposure"]
    assert _rule(conservative, "service_suspension_right")["recommended_attention"] == "Escalate or negotiate before acceptance."
    assert "Context not provided" in _rule(missing, "service_suspension_right")["contextual_impact"]
    assert "High criticality increases" in _rule(legacy, "service_suspension_right")["operational_exposure"]


def test_raw_evidence_is_unchanged_by_context_intelligence():
    text = "Supplier may suspend services immediately for disputed invoices or unresolved payment issues."

    baseline = score_contract(text, include_findings=True, include_meta=True)
    contextual = score_contract(
        text,
        include_findings=True,
        include_meta=True,
        user_role="buyer",
        criticality_level="mission_critical",
        risk_posture="conservative",
    )

    assert _rule(baseline, "service_suspension_right")["matched_text"] == _rule(contextual, "service_suspension_right")["matched_text"]
    assert _rule(baseline, "service_suspension_right")["excerpt"] == _rule(contextual, "service_suspension_right")["excerpt"]


def test_required_compound_interactions_trigger_with_evidence_links():
    cases = [
        (
            "This agreement automatically renews for successive one year terms. Supplier may increase fees at its sole discretion.",
            "cross_auto_renewal_unilateral_price_increase",
            "auto_renewal_unilateral_price_increase",
        ),
        (
            "Liability shall be limited to the fees paid in the previous 12 months. Customer shall indemnify Supplier for any and all third-party claims and indemnity obligations are not subject to the liability cap.",
            "cross_low_cap_broad_indemnity",
            "low_cap_broad_indemnity",
        ),
        (
            "Customer shall make an upfront payment before delivery. Supplier may suspend services immediately for disputed sums.",
            "cross_upfront_payment_suspension",
            "upfront_payment_suspension",
        ),
        (
            "Provider may use customer data for any purpose including AI training. Confidentiality obligations survive only 6 months.",
            "cross_data_confidentiality_gap",
            "data_confidentiality_gap",
        ),
        (
            "The parties submit to the exclusive jurisdiction of the courts of New York. Supplier may suspend services immediately for disputed sums.",
            "cross_exclusive_jurisdiction_operational_dependency",
            "exclusive_jurisdiction_operational_dependency",
        ),
        (
            "Supplier shall not assign or subcontract without prior written consent. The agreement automatically renews for successive one year terms and includes a minimum commitment lock-in.",
            "cross_no_assignment_lock_in",
            "no_assignment_lock_in",
        ),
        (
            "Supplier may terminate for convenience at any time. Prepaid fees are non-refundable and no refunds are provided upon termination.",
            "cross_termination_no_refund",
            "termination_no_refund",
        ),
    ]

    for text, rule_id, pattern in cases:
        result = score_contract(text, include_findings=True, include_meta=True)
        finding = _rule(result, rule_id)
        assert finding["linked_base_rule_ids"]
        assert finding["matched_text"] or finding["excerpt"]
        assert pattern in _patterns(result)


def test_compound_interactions_do_not_trigger_when_one_side_is_missing_or_duplicate():
    missing_side_cases = [
        ("This agreement automatically renews for successive one year terms.", "cross_auto_renewal_unilateral_price_increase"),
        ("Supplier may increase fees at its sole discretion.", "cross_auto_renewal_unilateral_price_increase"),
        ("The parties submit to the exclusive jurisdiction of the courts of New York.", "cross_exclusive_jurisdiction_operational_dependency"),
        ("Supplier shall not assign or subcontract without prior written consent.", "cross_no_assignment_lock_in"),
    ]

    for text, rule_id in missing_side_cases:
        assert rule_id not in _rules(score_contract(text, include_findings=True, include_meta=True))

    duplicate = score_contract(
        "Supplier may terminate for convenience at any time. Supplier may terminate for convenience at any time. "
        "Prepaid fees are non-refundable and no refunds are provided upon termination.",
        include_findings=True,
        include_meta=True,
    )
    assert [finding["rule_id"] for finding in duplicate["findings"]].count("cross_termination_no_refund") == 1


def test_decision_posture_outputs_are_deterministic_and_context_sensitive():
    high = score_contract(
        "Supplier may suspend services immediately for disputed sums. This agreement automatically renews for successive one year terms. Supplier may increase fees at its sole discretion.",
        include_findings=True,
        include_meta=True,
        user_role="customer",
        contract_type="saas",
        criticality_level="mission_critical",
        risk_posture="balanced",
    )
    low = score_contract("This agreement starts on Monday.", include_findings=True, include_meta=True, risk_posture="balanced")
    balanced = score_contract("Supplier may suspend services immediately for disputed sums.", include_findings=True, include_meta=True)
    conservative = score_contract("Supplier may suspend services immediately for disputed sums.", include_findings=True, include_meta=True, risk_posture="conservative")
    missing = score_contract("Supplier may suspend services immediately for disputed sums.", include_findings=True, include_meta=True)

    assert high["decision_posture"] == "escalate internally"
    assert high["escalation_reason"]
    assert high["decision_posture_evidence"]
    assert low["decision_posture"] in {"monitor only", "acceptable"}
    assert conservative["decision_posture"] != balanced["decision_posture"]
    assert missing["recommended_next_step"]


def test_policy_profile_changes_posture_without_tenant_storage():
    result = score_contract(
        "Customer shall indemnify Supplier for any and all third-party claims and indemnity obligations are not subject to the liability cap.",
        include_findings=True,
        include_meta=True,
        policy_profile={"uncapped_indemnity": "reject"},
    )

    assert result["decision_posture"] == "reject"
    assert result["meta"]["policy_trace"][0]["policy_key"] == "uncapped_indemnity"


def test_org_policy_changes_posture_is_isolated_and_audited(account_client):
    client, session_factory = account_client
    first = create_account(session_factory, plan_name="business", subscription_status="active")
    second = create_account(session_factory, plan_name="business", subscription_status="active")
    first_token = _login_account(client, first)
    second_token = _login_account(client, second)

    update = client.put(
        "/account/policy",
        headers=_auth(first_token),
        json={"policy": {"uncapped_indemnity": "reject"}, "note": "No uncapped indemnity."},
    )
    assert update.status_code == 200

    text = "Customer shall indemnify Supplier for any and all third-party claims and indemnity obligations are not subject to the liability cap."
    first_scan = _scan(client, first_token, text)
    second_scan = _scan(client, second_token, text)

    assert first_scan["decision_posture"] == "reject"
    assert second_scan["decision_posture"] != "reject"
    with session_factory() as db:
        audits = db.execute(select(OrganizationRiskPolicyAudit)).scalars().all()
        assert len(audits) == 1
        assert audits[0].org_id == first["org_id"]


def test_org_threshold_and_missing_policy_safe_defaults(account_client):
    client, session_factory = account_client
    account = create_account(session_factory, plan_name="business", subscription_status="active")
    token = _login_account(client, account)

    no_policy = _scan(client, token, "This agreement starts on Monday.", deal_value="GBP 300,000")
    assert no_policy["decision_posture"] == "monitor only"

    update = client.put(
        "/account/policy",
        headers=_auth(token),
        json={"policy": {"deal_value_threshold": "legal_review_over_250k"}},
    )
    assert update.status_code == 200

    threshold = _scan(client, token, "This agreement starts on Monday.", deal_value="GBP 300,000")
    assert threshold["decision_posture"] == "escalate internally"
    assert threshold["meta"]["policy_trace"][0]["policy_key"] == "deal_value_threshold"
