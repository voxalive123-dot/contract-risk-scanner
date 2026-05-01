import pytest

from analyzer.scorer import score_contract


def _rule_ids(result):
    return {finding["rule_id"] for finding in result["findings"]}


def _cross_adjustments(result):
    return [
        adjustment
        for adjustment in result["meta"]["score_adjustments"]
        if adjustment.get("type") == "cross_clause"
    ]


def _pattern_adjustment(result, pattern):
    return next(
        adjustment
        for adjustment in _cross_adjustments(result)
        if adjustment.get("pattern") == pattern
    )


@pytest.mark.parametrize(
    ("text", "pattern", "rule_id", "title"),
    [
        (
            "Liability shall be limited to the fees paid in the previous 12 months. "
            "Customer shall defend, indemnify and hold harmless Provider against any "
            "and all third-party claims, and indemnity obligations are not subject to "
            "the liability cap.",
            "low_cap_broad_indemnity",
            "cross_low_cap_broad_indemnity",
            "Liability cap may be weakened by indemnity obligations outside the cap",
        ),
        (
            "Supplier may terminate for convenience at any time. Prepaid fees are "
            "non-refundable and no refunds are provided upon termination.",
            "termination_no_refund",
            "cross_termination_no_refund",
            "Termination rights combined with lack of refund may create asymmetric exposure",
        ),
        (
            "Provider may use customer data for any purpose, including AI training "
            "and analytics. Confidentiality obligations survive only 6 months and "
            "confidential information carve-outs include residual knowledge.",
            "data_confidentiality_gap",
            "cross_data_confidentiality_gap",
            "Broad data rights combined with weak confidentiality may increase governance risk",
        ),
        (
            "Customer shall make an upfront payment before delivery. Supplier may "
            "suspend services immediately for disputed sums or unresolved payment issues.",
            "upfront_payment_suspension",
            "cross_upfront_payment_suspension",
            "Upfront payment combined with supplier suspension rights may create operational exposure",
        ),
    ],
)
def test_cross_clause_synthesis_positive_patterns(text, pattern, rule_id, title):
    result = score_contract(text, include_findings=True, include_meta=True)

    finding = next(finding for finding in result["findings"] if finding["rule_id"] == rule_id)
    adjustment = _pattern_adjustment(result, pattern)

    assert finding["title"] == title
    assert finding["pattern"] == pattern
    assert finding["synthesis_pattern"] == pattern
    assert finding["confidence"] > 0
    assert finding["linked_base_rule_ids"]
    assert finding["audit"]["version"]
    assert adjustment["impact"] == 1
    assert adjustment["effect"] == 1
    assert pattern in result["meta"]["synthesis_patterns_triggered"]


@pytest.mark.parametrize(
    ("text", "pattern", "rule_id"),
    [
        (
            "Liability shall be limited to the fees paid in the previous 12 months. "
            "Each party is responsible for its own third-party claims.",
            "low_cap_broad_indemnity",
            "cross_low_cap_broad_indemnity",
        ),
        (
            "Supplier may terminate for convenience at any time. Unused prepaid fees "
            "are subject to a pro-rata refund.",
            "termination_no_refund",
            "cross_termination_no_refund",
        ),
        (
            "Provider may use customer data for any purpose. Confidentiality obligations "
            "survive for five years and confidential information must be returned or destroyed.",
            "data_confidentiality_gap",
            "cross_data_confidentiality_gap",
        ),
        (
            "Customer shall make an upfront payment before delivery. Services continue "
            "throughout the paid term unless both parties agree otherwise.",
            "upfront_payment_suspension",
            "cross_upfront_payment_suspension",
        ),
    ],
)
def test_cross_clause_synthesis_negative_patterns(text, pattern, rule_id):
    result = score_contract(text, include_findings=True, include_meta=True)

    assert rule_id not in _rule_ids(result)
    assert pattern not in result["meta"]["synthesis_patterns_triggered"]


def test_cross_clause_synthesis_preserves_base_findings_in_mixed_contract():
    text = (
        "Liability shall be limited to the fees paid in the previous 12 months. "
        "Customer shall defend, indemnify and hold harmless Provider against any and all "
        "third-party claims, and indemnity obligations are not subject to the liability cap. "
        "Supplier may terminate for convenience at any time. Prepaid fees are non-refundable "
        "and no refunds are provided upon termination. Provider may use customer data for any "
        "purpose, including AI training and analytics. Confidentiality obligations survive only "
        "6 months and confidential information carve-outs include residual knowledge. Customer "
        "shall make an upfront payment before delivery. Supplier may suspend services immediately "
        "for disputed sums or unresolved payment issues."
    )

    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = _rule_ids(result)

    assert {
        "liability_cap_present",
        "indemnity_one_way",
        "termination_for_convenience_counterparty",
        "non_refundable_fees",
        "broad_customer_data_use",
        "confidentiality_survival_gap_or_imbalance",
        "service_suspension_right",
    }.issubset(rule_ids)
    assert {
        "cross_low_cap_broad_indemnity",
        "cross_termination_no_refund",
        "cross_data_confidentiality_gap",
        "cross_upfront_payment_suspension",
    }.issubset(rule_ids)


def test_cross_clause_synthesis_score_adjustment_is_capped_and_modest():
    text = (
        "Liability shall be limited to the fees paid in the previous 12 months. "
        "Customer shall defend, indemnify and hold harmless Provider against any and all "
        "third-party claims, and indemnity obligations are not subject to the liability cap. "
        "Supplier may terminate for convenience at any time. Prepaid fees are non-refundable "
        "and no refunds are provided upon termination. Provider may use customer data for any "
        "purpose, including AI training and analytics. Confidentiality obligations survive only "
        "6 months and confidential information carve-outs include residual knowledge. Customer "
        "shall make an upfront payment before delivery. Supplier may suspend services immediately "
        "for disputed sums or unresolved payment issues."
    )

    result = score_contract(text, include_findings=True, include_meta=True)
    cross_adjustments = _cross_adjustments(result)

    assert sum(int(adjustment["impact"]) for adjustment in cross_adjustments) <= 4
    assert all(adjustment["impact"] == 1 for adjustment in cross_adjustments)
    assert len(result["meta"]["synthesis_patterns_triggered"]) <= 4


def test_cross_clause_synthesis_does_not_duplicate_synthesized_findings():
    text = (
        "Supplier may terminate for convenience at any time. Supplier may terminate for "
        "convenience at any time. Prepaid fees are non-refundable and no refunds are provided "
        "upon termination. No refunds are provided after cancellation."
    )

    result = score_contract(text, include_findings=True, include_meta=True)
    rule_ids = [finding["rule_id"] for finding in result["findings"]]

    assert rule_ids.count("cross_termination_no_refund") == 1
    assert result["meta"]["synthesis_patterns_triggered"].count("termination_no_refund") == 1


def test_cross_clause_synthesis_output_schema_remains_compatible():
    result = score_contract(
        "Supplier may terminate for convenience at any time. Prepaid fees are "
        "non-refundable and no refunds are provided upon termination.",
        include_findings=True,
        include_meta=True,
        jurisdiction="uk",
        sector="SaaS",
        contract_type="subscription",
        user_role="buyer",
        objective="renewal review",
    )

    assert isinstance(result["risk_score"], int)
    assert result["severity"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(result["flags"], list)
    assert isinstance(result["findings"], list)
    assert "ruleset_version" in result["meta"]
    assert result["meta"]["context_profile_used"]["jurisdiction"] == "uk"
    assert result["meta"]["context_profile_used"]["sector"] == "saas"
    assert result["meta"]["context_profile_used"]["risk_positioning"]
    assert result["meta"]["risk_appetite"] == "balanced"
    assert result["meta"]["synthesis_patterns_triggered"] == ["termination_no_refund"]
