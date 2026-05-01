from analyzer.scorer import score_contract


def rule_ids(text: str) -> set[str]:
    return {finding["rule_id"] for finding in score_contract(text, include_findings=True, include_meta=True)["findings"]}


def assert_rule(text: str, rule_id: str) -> None:
    result = score_contract(text, include_findings=True, include_meta=True)
    ids = {finding["rule_id"] for finding in result["findings"]}
    assert rule_id in ids
    finding = next(f for f in result["findings"] if f["rule_id"] == rule_id)
    assert finding["matched_text"]
    assert finding["excerpt"]
    assert result["risk_score"] > 0


def assert_no_rule(text: str, rule_id: str) -> None:
    assert rule_id not in rule_ids(text)


def test_auto_renewal_hidden_cancellation_burden_positive_and_negative():
    assert_rule(
        "The subscription renews automatically unless cancellation is completed in the account portal before renewal; failure to cancel results in renewal and no refunds.",
        "auto_renewal_hidden_cancellation_burden",
    )
    assert_no_rule(
        "The agreement does not automatically renew. Customer may cancel by email or written notice before the term ends.",
        "auto_renewal_hidden_cancellation_burden",
    )


def test_payment_withholding_dispute_charge_leverage_positive_and_negative():
    assert_rule(
        "Customer may withhold any amounts pending acceptance. Invoices are deemed accepted unless disputed within 7 days, and overdue balances carry an administrative charge.",
        "payment_withholding_dispute_charge_leverage",
    )
    assert_no_rule(
        "Disputed amounts may be withheld, but undisputed amounts shall be paid when due and invoice disputes may be raised within 30 days.",
        "payment_withholding_dispute_charge_leverage",
    )


def test_audit_access_cost_confidentiality_positive_and_negative():
    assert_rule(
        "Supplier may audit Customer systems, logs, data, and records at any time, and Customer shall reimburse all audit costs.",
        "audit_access_cost_confidentiality",
    )
    assert_no_rule(
        "Audit is limited to relevant records, not more than once per year, subject to confidentiality, and at Provider expense.",
        "audit_access_cost_confidentiality",
    )


def test_confidentiality_survival_gap_or_imbalance_positive_and_negative():
    assert_rule(
        "Confidentiality obligations end upon termination and no confidentiality obligations survive termination.",
        "confidentiality_survival_gap_or_imbalance",
    )
    assert_no_rule(
        "Confidentiality obligations survive for five years, trade secrets remain protected while they are trade secrets, and each party must return or destroy confidential information.",
        "confidentiality_survival_gap_or_imbalance",
    )


def test_data_transfer_anonymisation_processing_positive_and_negative():
    assert_rule(
        "Provider may transfer Customer Data to subprocessors without prior notice and may use anonymised data for analytics and product development.",
        "data_transfer_anonymisation_processing",
    )
    assert_no_rule(
        "Provider processes Customer Data only to provide the services, subject to applicable data protection law and standard contractual clauses, and will make no attempt to re-identify de-identified data.",
        "data_transfer_anonymisation_processing",
    )


def test_ip_ownership_and_broad_license_positive_and_negative():
    assert_rule(
        "Provider shall own all foreground IP, deliverables, work product, developments, and improvements created under the statement of work.",
        "ip_ownership_foreground_conflict",
    )
    assert_rule(
        "Customer grants Provider a perpetual irrevocable worldwide royalty-free licence to Customer background IP and Provider may use residual knowledge and derivative works.",
        "ip_broad_license_or_residuals",
    )
    assert_no_rule(
        "Customer shall own the deliverables and foreground IP. Provider receives a licence solely to provide the services and has no right to use residual knowledge.",
        "ip_ownership_foreground_conflict",
    )
    assert_no_rule(
        "Customer shall own the deliverables and foreground IP. Provider receives a licence solely to provide the services and has no right to use residual knowledge.",
        "ip_broad_license_or_residuals",
    )


def test_unilateral_change_control_scope_terms_positive_and_negative():
    assert_rule(
        "Provider may change service levels, services, operational procedures, and material terms upon notice without Customer approval.",
        "unilateral_change_control_scope_terms",
    )
    assert_no_rule(
        "Changes to scope, services, or fees require mutual written agreement through a change order signed by both parties.",
        "unilateral_change_control_scope_terms",
    )


def test_force_majeure_broad_or_prolonged_positive_and_negative():
    assert_rule(
        "Force majeure excuses payment obligations and includes supply chain failure without liability; termination is available only after 120 days.",
        "force_majeure_broad_or_prolonged",
    )
    assert_no_rule(
        "Force majeure does not excuse payment obligations and either party may terminate after 30 days of continuing force majeure.",
        "force_majeure_broad_or_prolonged",
    )


def test_weak_sla_service_remedy_suspension_positive_and_negative():
    assert_rule(
        "Uptime is a target only and not a commitment. Service credits are at Provider discretion and no service credits apply for downtime.",
        "weak_sla_service_remedy_suspension",
    )
    assert_no_rule(
        "Provider commits to 99.9% uptime with service credits in addition to other remedies for service level failures.",
        "weak_sla_service_remedy_suspension",
    )


def test_liquidated_damages_financial_exposure_positive_and_negative():
    assert_rule(
        "Liquidated damages of a fixed amount are payable for each day of delay and are cumulative with other remedies.",
        "liquidated_damages_financial_exposure",
    )
    assert_no_rule(
        "The parties agree this is not liquidated damages and no liquidated damages apply.",
        "liquidated_damages_financial_exposure",
    )


def test_restrictive_covenant_positive_and_careful_rationale():
    text = "Customer shall not solicit Supplier employees for 24 months and the restriction applies to affiliates and group companies."
    result = score_contract(text, include_findings=True, include_meta=True)
    finding = next(f for f in result["findings"] if f["rule_id"] == "restrictive_covenant_non_solicit_non_compete")
    assert "may require legal review" in finding["rationale"]
    assert "enforceability-sensitive" in finding["rationale"]
    assert "enforceable" not in finding["rationale"].lower().replace("enforceability-sensitive", "")


def test_cross_payment_leverage_includes_withholding_suspension_and_late_fees():
    text = (
        "Customer may withhold any amounts pending acceptance. Payment is due within 7 days. "
        "Provider may suspend access immediately for non-payment. Overdue amounts accrue interest at 1.5% per month."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    ids = {f["rule_id"] for f in result["findings"]}
    assert "payment_withholding_dispute_charge_leverage" in ids
    assert "cross_payment_leverage_stack" in ids


def test_cross_audit_data_confidentiality_exposure_triggers_conservatively():
    text = (
        "Customer shall reimburse all audit costs and audit findings may be shared with affiliates. "
        "Provider may transfer Customer Data to subprocessors without prior notice. "
        "Confidentiality obligations end upon termination."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    ids = {f["rule_id"] for f in result["findings"]}
    assert "audit_access_cost_confidentiality" in ids
    assert "data_transfer_anonymisation_processing" in ids
    assert "confidentiality_survival_gap_or_imbalance" in ids
    assert "cross_audit_data_confidentiality_exposure" in ids
    assert any(adj.get("rule_id") == "cross_audit_data_confidentiality_exposure" and adj.get("effect") <= 2 for adj in result["meta"]["score_adjustments"])


def test_cross_change_control_weak_remedies_triggers_without_schema_change():
    text = (
        "Provider may change service levels and operational procedures upon notice without Customer approval. "
        "Uptime is a target only and not a commitment, and service credits are at Provider discretion."
    )
    result = score_contract(text, include_findings=True, include_meta=True)
    ids = {f["rule_id"] for f in result["findings"]}
    assert "cross_change_control_weak_remedies" in ids
    assert {"rule_id", "category", "title", "severity", "weight", "matched_text", "excerpt"}.issubset(result["findings"][0].keys())
    assert {"ruleset_version", "score_adjustments", "top_risks", "risk_appetite"}.issubset(result["meta"].keys())


def test_cross_ip_asset_leakage_and_force_majeure_lock_in():
    ip_text = (
        "Provider shall own all foreground IP and deliverables. Customer grants Provider a perpetual irrevocable worldwide royalty-free licence "
        "to background IP, and Provider may use residual knowledge and derivative works."
    )
    ip_result = score_contract(ip_text, include_findings=True, include_meta=True)
    assert "cross_ip_asset_leakage" in {f["rule_id"] for f in ip_result["findings"]}

    fm_text = (
        "Force majeure includes supply chain failure without liability and termination is available only after 120 days. "
        "Customer may not terminate for convenience during the term."
    )
    fm_result = score_contract(fm_text, include_findings=True, include_meta=True)
    assert "cross_force_majeure_continuity_lock_in" in {f["rule_id"] for f in fm_result["findings"]}


def test_balanced_clause_package_does_not_trigger_new_cross_family_stacks():
    text = (
        "Renewal requires mutual written agreement. Fees are payable within 30 days and disputes may be raised within 30 days. "
        "Audits occur once per year on reasonable notice, subject to confidentiality and at Provider expense. "
        "Customer owns deliverables and Provider receives a licence solely to provide the services. "
        "Force majeure does not excuse payment obligations and either party may terminate after 30 days. "
        "Service credits are in addition to other remedies."
    )
    ids = rule_ids(text)
    assert "cross_audit_data_confidentiality_exposure" not in ids
    assert "cross_change_control_weak_remedies" not in ids
    assert "cross_ip_asset_leakage" not in ids
    assert "cross_force_majeure_continuity_lock_in" not in ids
