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


def test_payment_leverage_stack_not_triggered_by_single_suspension_clause():
    text = "Provider may suspend access immediately for non-payment until payment is received."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "service_suspension_right" in rule_ids
    assert "cross_payment_leverage_stack" not in rule_ids



def test_payment_leverage_stack_triggers_for_short_window_suspension_and_interest():
    text = (
        "Payment is due within 7 days of invoice. Provider may suspend access immediately for non-payment until payment is received. "
        "Overdue amounts accrue interest at 1.5% per month until paid."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}
    adjustments = result["meta"]["score_adjustments"]

    assert "payment_deadline_pressure" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "fee_acceleration_late_fee_exposure" in rule_ids
    assert "cross_payment_leverage_stack" in rule_ids
    assert any(adj.get("rule_id") == "cross_payment_leverage_stack" for adj in adjustments)
    assert result["severity"] in {"MEDIUM", "HIGH"}
    assert result["risk_score"] >= 8



def test_payment_leverage_stack_triggers_for_acceleration_plus_suspension():
    text = (
        "Upon default, all outstanding amounts become immediately due and payable. Supplier may suspend the services "
        "for non-payment without notice or cure period."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "fee_acceleration_late_fee_exposure" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "cross_payment_leverage_stack" in rule_ids



def test_non_refundable_fees_detected_without_triggering_payment_stack_alone():
    text = "All prepaid fees are non-refundable and no refunds will be issued after termination."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "non_refundable_fees" in rule_ids
    assert "cross_payment_leverage_stack" not in rule_ids



def test_cross_payment_exit_pressure_not_triggered_for_payment_only_case():
    text = (
        "Payment is due within 7 days of invoice. Provider may suspend access immediately for non-payment "
        "until payment is received."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "payment_deadline_pressure" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "cross_payment_leverage_stack" in rule_ids
    assert "cross_payment_exit_pressure" not in rule_ids



def test_cross_payment_exit_pressure_not_triggered_for_exit_only_case():
    text = (
        "This agreement renews automatically for successive 12 month terms unless either party gives "
        "30 days written notice of non-renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "cross_payment_exit_pressure" not in rule_ids



def test_cross_payment_exit_pressure_triggers_for_payment_plus_renewal_pressure():
    text = (
        "Payment is due within 7 days of invoice. Provider may suspend access immediately for non-payment until payment is received. "
        "This agreement renews automatically unless Customer gives 30 days written notice of non-renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}
    adjustments = result["meta"]["score_adjustments"]

    assert "payment_deadline_pressure" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "cross_payment_leverage_stack" in rule_ids
    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "cross_payment_exit_pressure" in rule_ids
    assert any(adj.get("rule_id") == "cross_payment_exit_pressure" for adj in adjustments)



def test_cross_payment_exit_pressure_triggers_for_payment_plus_termination_constraint():
    text = (
        "Provider may suspend access immediately for non-payment until payment is received. "
        "Transition assistance will be provided at Provider's then-current rates."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "service_suspension_right" in rule_ids
    assert "termination_assistance_exit_dependency" in rule_ids
    assert "cross_payment_exit_pressure" in rule_ids



def test_cross_payment_exit_pressure_guardrail_does_not_trigger_without_underlying_rules():
    text = (
        "Invoices are payable in the ordinary course. Either party may terminate this agreement on reasonable notice."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_payment_exit_pressure" not in {f["rule_id"] for f in result["findings"]}


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


def test_cross_renewal_lock_in_plus_price_increase_triggers():
    text = (
        "This agreement renews automatically for successive periods of 12 months unless either party gives at least "
        "30 days written notice of non-renewal. Upon renewal, the fees may increase at Supplier's discretion."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}
    adjustments = result["meta"]["score_adjustments"]

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "renewal_long_commitment" in rule_ids
    assert "renewal_price_increase_on_renewal" in rule_ids
    assert "cross_renewal_price_lock_in" in rule_ids
    assert any(adj.get("rule_id") == "cross_renewal_price_lock_in" for adj in adjustments)
    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 10


def test_cross_renewal_lock_in_not_triggered_by_simple_renewal_alone():
    text = "This agreement renews automatically for successive terms unless either party gives notice of non-renewal."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_renewal_price_lock_in" not in {f["rule_id"] for f in result["findings"]}


def test_cross_renewal_lock_in_not_triggered_by_ordinary_price_clause_alone():
    text = "Fees are payable within 30 days and may be revised by mutual agreement at renewal."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_renewal_price_lock_in" not in {f["rule_id"] for f in result["findings"]}


def test_cross_renewal_lock_in_not_triggered_by_generic_price_increase_plus_renewal_pressure():
    text = (
        "This agreement renews automatically unless Customer gives 30 days written notice of non-renewal. "
        "Supplier may increase pricing on written notice at any time during the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "unilateral_price_increase" in rule_ids
    assert "cross_renewal_price_lock_in" not in rule_ids


def test_cross_unilateral_variation_limited_exit_triggers():
    text = (
        "Provider may change pricing and service scope upon notice to Customer. This agreement renews automatically "
        "unless Customer gives notice of non-renewal 30 days before expiry."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "unilateral_price_increase" in rule_ids
    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "cross_unilateral_variation_limited_exit" in rule_ids
    assert "cross_renewal_price_lock_in" not in rule_ids
    assert any(
        adj.get("rule_id") == "cross_unilateral_variation_limited_exit"
        for adj in result["meta"]["score_adjustments"]
    )


def test_cross_unilateral_variation_limited_exit_not_triggered_by_balanced_language():
    text = (
        "This agreement may be amended only by mutual written agreement. Either party may terminate for convenience "
        "on 30 days written notice."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_unilateral_variation_limited_exit" not in {f["rule_id"] for f in result["findings"]}


def test_cross_variation_payment_leverage_triggers_with_price_change_and_payment_pressure():
    text = (
        "Supplier may increase fees on written notice at any time during the term. "
        "Payment is due within 7 days of invoice and Supplier may suspend services immediately for non-payment."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "unilateral_price_increase" in rule_ids
    assert "payment_deadline_pressure" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "cross_variation_payment_leverage" in rule_ids
    assert "cross_payment_leverage_stack" in rule_ids


def test_cross_variation_payment_leverage_not_triggered_by_variation_alone():
    text = "Supplier may increase fees on written notice at any time during the term."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_variation_payment_leverage" not in {f["rule_id"] for f in result["findings"]}


def test_cross_suspension_payment_control_triggers_with_suspension_and_payment_penalty_support():
    text = (
        "Provider may suspend services immediately for non-payment until payment is received. "
        "Overdue amounts accrue interest at 1.5% per month and payment is due within 7 days of invoice."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "service_suspension_right" in rule_ids
    assert "payment_deadline_pressure" in rule_ids
    assert "fee_acceleration_late_fee_exposure" in rule_ids
    assert "cross_suspension_payment_control" in rule_ids


def test_cross_suspension_payment_control_not_triggered_by_suspension_alone():
    text = "Provider may suspend services immediately for non-payment until payment is received."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_suspension_payment_control" not in {f["rule_id"] for f in result["findings"]}


def test_cross_control_without_reciprocal_exit_triggers_for_control_stack_and_renewal_lock_in():
    text = (
        "Supplier may increase fees on notice and may subcontract the services without prior written consent. "
        "This agreement renews automatically for successive 12 month terms unless Customer gives 30 days written notice of non-renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}
    meta = result["meta"]

    assert "unilateral_price_increase" in rule_ids
    assert "subcontracting_without_consent" in rule_ids
    assert "auto_renewal_silent" in rule_ids
    assert "renewal_notice_window_pressure" in rule_ids
    assert "cross_control_without_reciprocal_exit" in rule_ids
    assert "cross_unilateral_variation_limited_exit" in rule_ids
    assert "matched_rule_count" in meta
    assert "score_adjustments" in meta


def test_cross_control_without_reciprocal_exit_not_triggered_without_exit_pressure():
    text = "Supplier may increase fees on notice and may subcontract the services without prior written consent."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_control_without_reciprocal_exit" not in {f["rule_id"] for f in result["findings"]}


def test_auto_renewal_notice_trap_detected_for_90_day_pre_renewal_notice():
    text = (
        "This agreement renews automatically for successive 12-month periods unless the customer gives written notice "
        "at least 90 days before the renewal date."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "auto_renewal_notice_trap" in {f["rule_id"] for f in result["findings"]}


def test_early_termination_fee_detected_for_remaining_fees_due_on_exit():
    text = "If Customer terminates early, all remaining fees for the then-current term become immediately payable."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "early_termination_fee" in {f["rule_id"] for f in result["findings"]}


def test_no_termination_for_convenience_customer_detected():
    text = "Customer may not terminate this agreement for convenience and may terminate only for cause."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "no_termination_for_convenience_customer" in {f["rule_id"] for f in result["findings"]}


def test_minimum_commitment_lock_in_detected():
    text = "Customer agrees to a minimum term of 24 months and minimum committed fees during that period."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "minimum_commitment_lock_in" in {f["rule_id"] for f in result["findings"]}


def test_cross_auto_renewal_notice_exit_trap_triggers_for_notice_burden_and_no_customer_exit():
    text = (
        "The agreement renews automatically unless Customer gives 90 days written notice before the renewal date. "
        "Customer may not terminate for convenience before the end of the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "auto_renewal_notice_trap" in rule_ids
    assert "no_termination_for_convenience_customer" in rule_ids
    assert "cross_auto_renewal_notice_exit_trap" in rule_ids


def test_cross_renewal_price_exit_trap_triggers_for_renewal_price_and_constrained_exit():
    text = (
        "The agreement renews automatically unless Customer gives 90 days written notice before the renewal date. "
        "Upon renewal, the fees may increase at Supplier's discretion. Customer may not terminate for convenience during the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "renewal_price_increase_on_renewal" in rule_ids
    assert "cross_renewal_price_exit_trap" in rule_ids
    assert "cross_renewal_price_lock_in" in rule_ids


def test_cross_termination_fee_lock_in_triggers_for_exit_cost_and_weak_exit():
    text = (
        "If Customer terminates early, all remaining fees for the then-current term become immediately payable. "
        "Customer may not terminate for convenience except at the end of the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "early_termination_fee" in rule_ids
    assert "no_termination_for_convenience_customer" in rule_ids
    assert "cross_termination_fee_lock_in" in rule_ids


def test_cross_supplier_control_customer_lock_in_triggers_for_control_rights_and_lock_in():
    text = (
        "Supplier may change pricing on notice, may suspend services for non-payment, and may subcontract without prior written consent. "
        "Customer may not terminate for convenience during the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "unilateral_price_increase" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "subcontracting_without_consent" in rule_ids
    assert "no_termination_for_convenience_customer" in rule_ids
    assert "cross_supplier_control_customer_lock_in" in rule_ids


def test_cross_exit_trap_stack_triggers_for_structural_lock_in_package():
    text = (
        "The agreement renews automatically for successive 12-month periods unless the customer gives written notice at least 90 days before the renewal date. "
        "Supplier may amend the fees for any renewal term by written notice. Customer may not terminate for convenience during the term. "
        "If customer terminates early, all remaining fees for the then-current term become immediately payable. "
        "Supplier may suspend services for unpaid invoices after 7 days."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}
    meta = result["meta"]

    assert "auto_renewal_notice_trap" in rule_ids
    assert "renewal_price_increase_on_renewal" in rule_ids
    assert "no_termination_for_convenience_customer" in rule_ids
    assert "early_termination_fee" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "cross_exit_trap_stack" in rule_ids
    assert "cross_auto_renewal_notice_exit_trap" in rule_ids
    assert "cross_termination_fee_lock_in" in rule_ids
    assert "risk_score" in result
    assert "severity" in result
    assert "findings" in result
    assert "confidence" in meta
    assert "score_adjustments" in meta
    assert "matched_rule_count" in meta
    assert "suppressed_rule_count" in meta
    assert "normalized_score" in meta
    assert "top_risks" in meta


def test_lower_risk_mutual_renewal_and_clear_exit_does_not_trigger_strong_exit_trap_synthesis():
    text = (
        "The agreement renews only by mutual written agreement. Either party may terminate for convenience on 30 days notice. "
        "Fees for renewal terms must be agreed in writing before renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "cross_auto_renewal_notice_exit_trap" not in rule_ids
    assert "cross_renewal_price_exit_trap" not in rule_ids
    assert "cross_exit_trap_stack" not in rule_ids


def test_isolated_price_increase_does_not_trigger_renewal_exit_trap():
    text = "Supplier may increase fees on notice during the term."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_renewal_price_exit_trap" not in {f["rule_id"] for f in result["findings"]}


def test_isolated_termination_fee_does_not_trigger_full_exit_trap_stack():
    text = "A cancellation fee equal to three months of fees applies upon early termination."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "early_termination_fee" in rule_ids
    assert "cross_exit_trap_stack" not in rule_ids


def test_cross_indemnity_cap_gap_triggers():
    text = (
        "Customer shall defend, indemnify, and hold Supplier harmless against all third-party claims. "
        "Liability is limited except that the cap is unclear and does not clearly apply to indemnity."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "cross_indemnity_cap_gap" in rule_ids
    assert any(
        adj.get("rule_id") == "cross_indemnity_cap_gap"
        for adj in result["meta"]["score_adjustments"]
    )


def test_cross_indemnity_cap_gap_not_triggered_by_narrow_indemnity_alone():
    text = "Each party shall indemnify the other to the extent caused by its own negligence."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_indemnity_cap_gap" not in {f["rule_id"] for f in result["findings"]}


def test_cross_indemnity_cap_gap_not_triggered_by_ordinary_limitation_alone():
    text = "Liability shall be limited to fees paid in the preceding 12 months."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_indemnity_cap_gap" not in {f["rule_id"] for f in result["findings"]}


def test_cross_forum_burden_mismatch_triggers_on_mismatched_locations():
    text = (
        "This agreement is governed by the laws of England and Wales. Any dispute shall be finally resolved by "
        "arbitration seated in Singapore."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "cross_forum_burden_mismatch" in rule_ids
    assert any(
        adj.get("rule_id") == "cross_forum_burden_mismatch"
        for adj in result["meta"]["score_adjustments"]
    )


def test_cross_forum_burden_mismatch_not_triggered_for_same_market_forum_package():
    text = (
        "This agreement is governed by the laws of California and the parties submit to the exclusive jurisdiction "
        "of the courts of California."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "cross_forum_burden_mismatch" not in {f["rule_id"] for f in result["findings"]}


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



def test_sector_playbook_classifies_saas_contract():
    text = (
        "This SaaS subscription provides access to the platform dashboard for named user accounts and API usage. "
        "Availability and uptime targets apply to the hosted service."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    playbook_ids = {item["id"] for item in result["meta"]["sector_playbooks"]}

    assert "saas_contract" in playbook_ids


def test_sector_playbook_classifies_supplier_service_contract():
    text = (
        "Supplier will provide the Services under each Statement of Work and Purchase Order, including delivery of the Deliverables and management of subcontractors."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    playbook_ids = {item["id"] for item in result["meta"]["sector_playbooks"]}

    assert "supplier_service_contract" in playbook_ids


def test_sector_playbook_classifies_data_heavy_contract():
    text = (
        "Provider will process Customer Data and Personal Data, may analyze Usage Data, and will document retention and deletion obligations for Aggregated Data."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    playbook_ids = {item["id"] for item in result["meta"]["sector_playbooks"]}

    assert "data_heavy_contract" in playbook_ids


def test_generic_short_clause_does_not_trigger_all_sector_playbooks():
    text = "Either party may terminate this agreement on written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["meta"]["sector_playbooks"] == []


def test_sector_saas_subscription_lock_in_triggers_for_saas_lock_in_stack():
    text = (
        "This SaaS subscription gives Customer access to the software platform dashboard and named user accounts. "
        "The agreement renews automatically for successive 12-month periods unless Customer gives at least 90 days written notice before the renewal date. "
        "Supplier may amend the fees for any renewal term by written notice. Customer may not terminate for convenience during the term. "
        "Supplier may suspend the hosted service for unpaid invoices after 7 days."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "saas_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "auto_renewal_notice_trap" in rule_ids
    assert "renewal_price_increase_on_renewal" in rule_ids
    assert "no_termination_for_convenience_customer" in rule_ids
    assert "sector_saas_subscription_lock_in" in rule_ids


def test_sector_saas_operational_dependency_triggers_for_suspension_and_transition_weakness():
    text = (
        "This SaaS platform provides API access and user accounts through the hosted service dashboard. "
        "Provider may suspend access immediately for non-payment until payment is received. "
        "Service credits are Customer's sole and exclusive remedy for downtime. "
        "Transition assistance will be provided at Provider's then-current rates."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "saas_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "service_suspension_right" in rule_ids
    assert "termination_assistance_exit_dependency" in rule_ids
    assert "sector_saas_operational_dependency" in rule_ids


def test_sector_supplier_control_stack_triggers_for_service_control_and_lock_in():
    text = (
        "Supplier will provide the Services under each Statement of Work and Purchase Order and may use subcontractors for Deliverables. "
        "Supplier may change pricing on notice and may subcontract without prior written consent. "
        "Customer may not terminate for convenience during the term."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "supplier_service_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "subcontracting_without_consent" in rule_ids
    assert "unilateral_price_increase" in rule_ids
    assert "sector_supplier_control_stack" in rule_ids


def test_sector_data_secondary_use_risk_triggers_for_data_use_sublicensing_and_retention():
    text = (
        "Provider processes Customer Data, Personal Data, and Usage Data and may use aggregated data and analytics for internal business purposes. "
        "Provider may use Customer Data for any purpose, may sublicense such rights without restriction, and may retain customer data after termination for business purposes."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "data_heavy_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "broad_customer_data_use" in rule_ids
    assert "broad_sublicensing_right" in rule_ids
    assert "data_retention_deletion_asymmetry" in rule_ids
    assert "sector_data_secondary_use_risk" in rule_ids


def test_sector_data_exit_residue_risk_triggers_for_retention_and_exit_weakness():
    text = (
        "Provider processes Customer Data and Personal Data. Provider may retain customer data after termination and has no obligation to return or delete customer data after termination. "
        "Transition assistance will be provided at Provider's then-current rates."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "data_heavy_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "data_retention_deletion_asymmetry" in rule_ids
    assert "termination_assistance_exit_dependency" in rule_ids
    assert "sector_data_exit_residue_risk" in rule_ids


def test_data_words_alone_do_not_trigger_sector_data_synthesis():
    text = (
        "Provider will process Customer Data and Personal Data only to perform the services and will return or delete the data on request."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "data_heavy_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "sector_data_secondary_use_risk" not in rule_ids
    assert "sector_data_exit_residue_risk" not in rule_ids


def test_saas_words_alone_do_not_trigger_saas_sector_synthesis():
    text = (
        "This SaaS platform subscription renews only by mutual written agreement. Either party may terminate for convenience on 30 days notice. "
        "Fees for any renewal term must be agreed in writing before renewal."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = {f["rule_id"] for f in result["findings"]}

    assert "saas_contract" in {item["id"] for item in result["meta"]["sector_playbooks"]}
    assert "sector_saas_subscription_lock_in" not in rule_ids
    assert "sector_saas_operational_dependency" not in rule_ids


def test_balanced_risk_appetite_remains_default_and_stable():
    text = (
        "Supplier may suspend services for unpaid invoices after 7 days. "
        "Customer may not terminate for convenience during the term."
    )
    implicit = score_contract(text, include_findings=True, include_meta=True)
    explicit = score_contract(text, include_findings=True, include_meta=True, risk_appetite="balanced")

    assert implicit["meta"]["risk_appetite"] == "balanced"
    assert explicit["meta"]["risk_appetite"] == "balanced"
    assert implicit["risk_score"] == explicit["risk_score"]
    assert implicit["flags"] == explicit["flags"]


def test_strict_and_conservative_risk_appetite_do_not_hide_findings():
    text = (
        "This SaaS subscription gives Customer access to the software platform dashboard and named user accounts. "
        "The agreement renews automatically for successive 12-month periods unless Customer gives at least 90 days written notice before the renewal date. "
        "Supplier may amend the fees for any renewal term by written notice. Customer may not terminate for convenience during the term. "
        "If Customer terminates early, all remaining fees become immediately payable."
    )
    balanced = score_contract(text, include_findings=True, include_meta=True)
    strict = score_contract(text, include_findings=True, include_meta=True, risk_appetite="strict")
    conservative = score_contract(text, include_findings=True, include_meta=True, risk_appetite="conservative")

    balanced_rules = {f["rule_id"] for f in balanced["findings"]}
    strict_rules = {f["rule_id"] for f in strict["findings"]}
    conservative_rules = {f["rule_id"] for f in conservative["findings"]}

    assert balanced_rules == strict_rules == conservative_rules
    assert strict["risk_score"] >= balanced["risk_score"]
    assert conservative["risk_score"] >= balanced["risk_score"]
    assert strict["risk_score"] <= balanced["risk_score"] + 1
    assert conservative["risk_score"] <= balanced["risk_score"] + 1
    assert strict["meta"]["risk_appetite_adjustments"]
    assert conservative["meta"]["risk_appetite_adjustments"]


def test_extended_meta_shape_includes_playbooks_audit_and_appetite_fields():
    text = (
        "This SaaS subscription gives Customer access to the software platform dashboard and named user accounts. "
        "The agreement renews automatically for successive 12-month periods unless Customer gives at least 90 days written notice before the renewal date. "
        "Supplier may amend the fees for any renewal term by written notice. Customer may not terminate for convenience during the term. "
        "Supplier may suspend the hosted service for unpaid invoices after 7 days."
    )
    result = score_contract(text, include_findings=True, include_meta=True, risk_appetite="strict")
    meta = result["meta"]

    assert "risk_score" in result
    assert "severity" in result
    assert "findings" in result
    assert "confidence" in meta
    assert "score_adjustments" in meta
    assert "matched_rule_count" in meta
    assert "suppressed_rule_count" in meta
    assert "normalized_score" in meta
    assert "top_risks" in meta
    assert "rule_families_detected" in meta
    assert "sector_playbooks" in meta
    assert "risk_appetite" in meta
    assert "risk_appetite_adjustments" in meta
    assert "derived_finding_count" in meta
    assert meta["risk_appetite"] == "strict"
    assert meta["derived_finding_count"] >= 1
