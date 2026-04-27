from analyzer.scorer import score_contract


def test_detect_unlimited_liability():
    text = "The supplier accepts unlimited liability."
    result = score_contract(text)

    assert result["risk_score"] >= 5
    assert "unlimited liability" in result["flags"]


def test_detect_termination_without_notice():
    text = "The agreement may terminate without notice."
    result = score_contract(text)

    assert result["risk_score"] >= 5
    assert "termination without notice" in result["flags"]


def test_no_risk_phrase():
    text = "This agreement starts on Monday."
    result = score_contract(text)

    assert result["risk_score"] == 0
    assert result["flags"] == []


def test_detect_selected_exclusive_jurisdiction():
    text = "The parties submit to the exclusive jurisdiction of the courts of New York."
    result = score_contract(text)

    assert result["risk_score"] >= 6
    assert "selected exclusive jurisdiction" in result["flags"]


def test_material_dispute_forum_signal_stays_review_elevating():
    text = (
        "This agreement is governed by the laws of California and the parties submit to the "
        "exclusive jurisdiction of the courts of California. Any dispute shall be resolved in "
        "the courts of California."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 6
    assert result["meta"]["normalized_score"] >= 28
    assert any(
        adjustment.get("rule_id") == "material_dispute_forum_floor"
        for adjustment in result["meta"]["score_adjustments"]
    )


def test_selected_governing_law_alone_is_not_low_signal():
    text = "This agreement is governed by the laws of California."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 6
    assert result["meta"]["normalized_score"] >= 28
    assert "selected governing law" in result["flags"]
    assert result["findings"][0]["matched_location"] == "California"


def test_simple_auto_renewal_clause_stays_low_signal():
    text = "This agreement shall renew automatically for successive terms unless either party gives notice of non-renewal."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] == "LOW"
    assert "silent or automatic renewal" in result["flags"]
    assert result["risk_score"] == 3


def test_auto_renewal_with_30_day_notice_window_is_review_elevating():
    text = (
        "This agreement shall renew automatically for successive terms unless either party gives "
        "at least 30 days written notice of non-renewal before the end of the then-current term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 5


def test_auto_renewal_with_long_renewal_period_is_review_elevating():
    text = (
        "This agreement shall renew automatically for successive periods of 12 months unless "
        "either party gives notice of non-renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_long_commitment" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 5


def test_auto_renewal_plus_price_increase_raises_payment_exposure():
    text = (
        "This agreement shall renew automatically for successive terms unless cancelled. "
        "Upon renewal, the fees may increase."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_price_increase_on_renewal" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 6


def test_auto_renewal_with_asymmetric_exit_rights_is_review_elevating():
    text = (
        "This agreement shall renew automatically for successive terms unless Customer gives at "
        "least 90 days written notice of non-renewal. Supplier may terminate for convenience at any time."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "termination_for_convenience_counterparty" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 7


def test_benign_monthly_renewal_clause_does_not_false_trigger_high_severity():
    text = (
        "This agreement may be renewed by mutual written agreement only. Either party may terminate "
        "on 60 days written notice before the next monthly period."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] != "HIGH"
    assert "auto renewal" not in result["flags"]


def test_explicit_no_auto_renewal_clause_does_not_trigger_auto_renewal_risk():
    text = "The Agreement does not automatically renew. Any renewal must be agreed in writing by both parties."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "auto_renewal_silent" not in {f["rule_id"] for f in result["findings"]}
    assert "silent or automatic renewal" not in result["flags"]


def test_mutual_written_renewal_only_clause_does_not_trigger_auto_renewal_risk():
    text = "The contract is not subject to automatic renewal and renewal only by mutual written agreement."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "auto_renewal_silent" not in {f["rule_id"] for f in result["findings"]}


def test_unilateral_variation_of_pricing_and_service_scope_is_review_elevating():
    text = (
        "Provider may change pricing, service scope, and service levels upon notice to Customer "
        "without further consent."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "unilateral_amendment_policy_reference" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 4


def test_mutual_written_variation_clause_does_not_over_escalate():
    text = "This agreement may be amended only by mutual written agreement signed by both parties."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "unilateral amendment" not in result["flags"]


def test_broad_audit_rights_trigger_without_overstating_reasonable_controls():
    risky = (
        "Third-party auditors may inspect Customer premises, systems, logs, and financial records "
        "on 24 hours notice at Customer cost."
    )
    risky_result = score_contract(risky, include_findings=True, include_meta=True)

    assert "intrusive audit rights" in risky_result["flags"]
    assert risky_result["risk_score"] >= 3

    safe = (
        "Audit is limited to relevant records upon reasonable notice during normal business hours, "
        "not more than once per year, subject to confidentiality, and at Provider expense."
    )
    safe_result = score_contract(safe, include_findings=True, include_meta=True)

    assert "intrusive audit rights" not in safe_result["flags"]


def test_payment_pressure_cluster_is_review_elevating():
    text = (
        "Invoices are due within 10 days. Provider may suspend access immediately for non-payment "
        "without a cure period. Customer shall pay all costs of collection, including attorneys' fees."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "payment_deadline_pressure" in rule_ids
    assert "payment_collection_cost_shifting" in rule_ids
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 5


def test_ordinary_payment_timing_stays_low_signal():
    text = "Invoices are payable within 30 days of receipt."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "short payment deadline pressure" not in result["flags"]


def test_one_sided_data_security_responsibility_is_review_elevating():
    text = (
        "Customer is solely responsible for passwords, credentials, unauthorized access, and any "
        "resulting security incident. Provider shall have no responsibility for unauthorized access."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "data_security_responsibility_imbalance" in rule_ids
    assert result["risk_score"] >= 4


def test_balanced_security_clause_does_not_over_escalate():
    text = (
        "Each party shall maintain reasonable security safeguards and Provider will implement "
        "appropriate technical and organizational measures."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "one sided data or security responsibility" not in result["flags"]


def test_exclusive_remedy_limitation_is_review_elevating():
    text = (
        "Replacement of the defective services or refund of fees paid is Customer's sole and "
        "exclusive remedy for service failure."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "exclusive_remedy_limitation" in rule_ids
    assert result["risk_score"] >= 3


def test_preserved_remedies_clause_does_not_false_trigger_exclusive_remedy():
    text = "Service credits are in addition to other remedies and do not exclude non-excludable statutory rights."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "exclusive remedy limitation" not in result["flags"]


def test_mutual_liability_cap_with_standard_carveouts_does_not_trigger_super_cap_exposure():
    text = (
        "Liability of each party is limited to the fees paid in the previous twelve (12) months, "
        "except for fraud, wilful misconduct, confidentiality breach, or liabilities which cannot lawfully be limited."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "liability_super_cap_carveout" not in {f["rule_id"] for f in result["findings"]}
    assert "liability cap carve-out or super-cap exposure" not in result["flags"]


def test_customer_only_uncapped_carveout_still_triggers_super_cap_exposure():
    text = (
        "Liability is capped at the fees paid in the previous 12 months, except that the cap shall not apply "
        "to Customer payment obligations, Customer indemnity obligations, or Customer breach claims."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "liability_super_cap_carveout" in {f["rule_id"] for f in result["findings"]}


def test_exclusive_jurisdiction_extracts_selected_courts():
    text = "The parties submit to the exclusive jurisdiction of the courts of California."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] == "MEDIUM"
    assert result["findings"][0]["matched_location"] == "California courts"


def test_arbitration_seat_extracts_selected_location():
    text = "Any dispute shall be finally resolved by arbitration seated in Singapore under the ICC Rules."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["findings"][0]["matched_location"] == "Singapore"


def test_uk_dominant_document_context_can_add_safe_forum_mismatch_note():
    text = (
        "This supplier agreement is entered into in England and Wales. The services will be "
        "performed from London for a United Kingdom customer. The parties submit to the exclusive "
        "jurisdiction of the courts of California."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["findings"][0]["matched_location"] == "California courts"
    assert "Selected forum appears different from the document's dominant geography." in result["findings"][0]["rationale"]
    assert result["findings"][0]["context_note"] == "Selected forum appears different from the document's dominant geography."


def test_no_forum_mismatch_note_when_document_geography_is_unclear():
    text = "The parties submit to the exclusive jurisdiction of the courts of California."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["findings"][0]["matched_location"] == "California courts"
    assert result["findings"][0]["context_note"] is None
