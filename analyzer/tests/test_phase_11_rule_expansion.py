from analyzer.scorer import score_contract


def rule_ids(text: str) -> set[str]:
    return {
        finding["rule_id"]
        for finding in score_contract(text, include_findings=True, include_meta=True)["findings"]
    }


def assert_rule(text: str, rule_id: str) -> None:
    result = score_contract(text, include_findings=True, include_meta=True)
    assert rule_id in {finding["rule_id"] for finding in result["findings"]}
    assert result["risk_score"] > 0


def assert_no_rule(text: str, rule_id: str) -> None:
    assert rule_id not in rule_ids(text)


def test_change_of_control_assignment_positive_negative_and_edge():
    assert_rule(
        "Supplier may assign this agreement in connection with a change of control without consent.",
        "change_of_control_assignment",
    )
    assert_no_rule(
        "A change of control requires prior written consent before any assignment may proceed.",
        "change_of_control_assignment",
    )
    assert_rule(
        "A change of control is deemed an assignment and may proceed without additional approval.",
        "change_of_control_assignment",
    )


def test_unilateral_amendment_policy_reference_positive_negative_and_edge():
    assert_rule(
        "Supplier may update the policies incorporated by reference and amended from time to time.",
        "unilateral_amendment_policy_reference",
    )
    assert_no_rule(
        "This agreement may be amended only by mutual written agreement of the parties.",
        "unilateral_amendment_policy_reference",
    )
    assert_rule(
        "Customer shall comply with security policies as updated by Supplier from time to time.",
        "unilateral_amendment_policy_reference",
    )


def test_fee_acceleration_late_fee_positive_negative_and_edge():
    assert_rule(
        "Upon termination, all remaining fees are immediately due and payable.",
        "fee_acceleration_late_fee_exposure",
    )
    assert_no_rule(
        "There is no acceleration of future fees and undisputed overdue amounts bear reasonable interest.",
        "fee_acceleration_late_fee_exposure",
    )
    assert_rule(
        "Overdue amounts accrue interest at 1.5% per month until paid.",
        "fee_acceleration_late_fee_exposure",
    )


def test_service_credits_sole_remedy_positive_negative_and_edge():
    assert_rule(
        "Service credits are Customer's sole and exclusive remedy for service level failures.",
        "service_credits_sole_remedy",
    )
    assert_no_rule(
        "Service credits are in addition to other remedies available under this agreement.",
        "service_credits_sole_remedy",
    )
    assert_rule(
        "The only remedy for downtime will be service credits calculated under the SLA.",
        "service_credits_sole_remedy",
    )


def test_publicity_name_use_positive_negative_and_edge():
    assert_rule(
        "Supplier may use Customer's name and logo in marketing materials.",
        "publicity_name_use_rights",
    )
    assert_no_rule(
        "Supplier may use Customer's name and logo only with prior written consent.",
        "publicity_name_use_rights",
    )
    assert_rule(
        "Supplier may identify Customer as a customer without consent in public customer lists.",
        "publicity_name_use_rights",
    )


def test_intrusive_audit_positive_negative_and_edge():
    assert_rule(
        "Supplier may audit Customer's books and records at any time during the term.",
        "intrusive_audit_rights",
    )
    assert_no_rule(
        "Audit may occur upon reasonable notice during normal business hours and not more than once per year.",
        "intrusive_audit_rights",
    )
    assert_rule(
        "Provider has the right to audit without notice and inspect systems at any time.",
        "intrusive_audit_rights",
    )


def test_data_retention_deletion_positive_negative_and_edge():
    assert_rule(
        "Provider may retain customer data after termination for internal business purposes.",
        "data_retention_deletion_asymmetry",
    )
    assert_no_rule(
        "Provider will return or delete customer data upon request and retain customer data only as required by law.",
        "data_retention_deletion_asymmetry",
    )
    assert_rule(
        "Provider has no obligation to return or delete customer data after termination.",
        "data_retention_deletion_asymmetry",
    )


def test_termination_assistance_exit_dependency_positive_negative_and_edge():
    assert_rule(
        "Termination assistance is subject to Provider's discretion and then-current rates.",
        "termination_assistance_exit_dependency",
    )
    assert_no_rule(
        "Provider will provide reasonable exit assistance for up to 30 days at no additional charge.",
        "termination_assistance_exit_dependency",
    )
    assert_rule(
        "Provider has no obligation to provide transition assistance after termination.",
        "termination_assistance_exit_dependency",
    )


def test_survival_clause_concentration_positive_negative_and_edge():
    assert_rule(
        "Indemnification, confidentiality, payment, and liability obligations survive termination.",
        "survival_clause_risk_concentration",
    )
    assert_no_rule(
        "Confidentiality obligations survive termination for two years and survival is limited to stated clauses.",
        "survival_clause_risk_concentration",
    )
    assert_rule(
        "All obligations survive termination indefinitely unless Supplier agrees otherwise.",
        "survival_clause_risk_concentration",
    )


def test_mixed_safe_and_risky_expansion_clauses_preserve_false_positive_controls():
    text = (
        "This agreement may be amended only by mutual written agreement. "
        "Supplier may use Customer's name and logo only with prior written consent. "
        "Service credits are Customer's sole and exclusive remedy for downtime. "
        "Provider may retain customer data after termination for internal business purposes. "
        "Audit may occur upon reasonable notice during normal business hours."
    )
    ids = rule_ids(text)

    assert "service_credits_sole_remedy" in ids
    assert "data_retention_deletion_asymmetry" in ids
    assert "unilateral_amendment_policy_reference" not in ids
    assert "publicity_name_use_rights" not in ids
    assert "intrusive_audit_rights" not in ids


def test_governing_law_foreign_or_unfamiliar_positive():
    assert_rule(
        "This agreement is governed by the laws of the State of New York.",
        "governing_law_foreign_or_unfamiliar",
    )


def test_exclusive_jurisdiction_foreign_forum_positive():
    assert_rule(
        "The parties submit to the exclusive jurisdiction of the courts of California.",
        "jurisdiction_exclusive_foreign_forum",
    )


def test_non_exclusive_jurisdiction_positive():
    assert_rule(
        "The courts of Singapore shall have non-exclusive jurisdiction over any dispute arising under this agreement.",
        "jurisdiction_non_exclusive_forum",
    )


def test_arbitration_forum_or_seat_positive():
    assert_rule(
        "Any dispute shall be finally resolved by arbitration seated in Geneva under the ICC Rules.",
        "arbitration_forum_or_seat",
    )


def test_generic_applicable_law_compliance_wording_does_not_trigger_governing_law_rules():
    text = "Each party shall comply with all applicable laws and regulations in performing this agreement."
    for rule_id in {
        "governing_law_foreign_or_unfamiliar",
        "jurisdiction_exclusive_foreign_forum",
        "jurisdiction_non_exclusive_forum",
        "arbitration_forum_or_seat",
        "venue_burden_foreign_court",
    }:
        assert_no_rule(text, rule_id)


def test_mixed_governing_law_and_forum_paragraph_is_not_noisily_duplicated():
    result = score_contract(
        (
            "This agreement is governed by the laws of California. "
            "The parties submit to the exclusive jurisdiction of the courts of California. "
            "Any dispute shall be finally resolved by arbitration seated in San Francisco, California."
        ),
        include_findings=True,
        include_meta=True,
    )

    jurisdiction_findings = [
        finding for finding in result["findings"] if finding["category"] == "jurisdiction"
    ]

    assert result["risk_score"] > 0
    assert len(jurisdiction_findings) == 1
    assert len(result["meta"].get("overlap_suppressions", [])) >= 1
    assert all("foreign" not in flag for flag in result["flags"])
