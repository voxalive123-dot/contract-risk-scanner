from analyzer.scorer import score_contract


def test_assignment_without_consent_positive():
    text = "Supplier may assign this Agreement to any third party without the Customer's consent."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "assignment_without_consent" in rule_ids
    assert result["risk_score"] > 0


def test_assignment_without_consent_negative_mutual_reasonable_consent():
    text = (
        "Neither party may assign this Agreement without prior written consent, "
        "such consent not to be unreasonably withheld."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "assignment_without_consent" not in rule_ids


def test_assignment_without_consent_negative_affiliate_carveout():
    text = (
        "Supplier may assign this Agreement without consent to an affiliate "
        "or in connection with a merger or sale of substantially all assets."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "assignment_without_consent" not in rule_ids

def test_termination_for_convenience_positive():
    text = "Supplier may terminate this Agreement for convenience at any time upon written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "termination_for_convenience_counterparty" in rule_ids
    assert result["risk_score"] > 0


def test_termination_for_convenience_negative_breach_based():
    text = (
        "Either party may terminate this Agreement for material breach "
        "if the other party fails to cure such breach after written notice."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "termination_for_convenience_counterparty" not in rule_ids

def test_termination_for_convenience_negative_mutual():
    text = "Either party may terminate this Agreement for convenience upon thirty days written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "termination_for_convenience_counterparty" not in rule_ids

def test_unilateral_price_increase_positive():
    text = "Supplier may increase the fees upon thirty days written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "unilateral_price_increase" in rule_ids
    assert result["risk_score"] > 0


def test_unilateral_price_increase_negative_cpi_indexed():
    text = "Supplier may increase the fees once per year in line with CPI upon thirty days written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "unilateral_price_increase" not in rule_ids

def test_service_suspension_right_positive():
    text = "Supplier may suspend the services at any time without liability upon written notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "service_suspension_right" in rule_ids
    assert result["risk_score"] > 0


def test_service_suspension_right_negative_non_payment():
    text = "Supplier may suspend the services for non-payment after reasonable notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "service_suspension_right" not in rule_ids


def test_service_suspension_right_negative_security_protection():
    text = (
        "Supplier may suspend the services to protect the security of the services "
        "and prevent security incidents."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "service_suspension_right" not in rule_ids


def test_indemnity_one_way_positive():
    text = "Customer shall defend, indemnify, and hold Supplier harmless against third-party claims."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "indemnity_one_way" in rule_ids
    assert result["risk_score"] > 0


def test_indemnity_one_way_negative_mutual():
    text = "Each party shall indemnify, defend, and hold the other harmless against third-party claims."
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]

    assert "indemnity_one_way" not in rule_ids

def test_commercial_control_cluster_compound_adjustment():
    text = (
        "Supplier may increase the fees upon thirty days written notice. "
        "Supplier may suspend the services at any time without liability. "
        "Supplier may terminate this Agreement for convenience at any time upon written notice."
    )
    result = score_contract(text, include_findings=True, include_meta=True)

    rule_ids = [f["rule_id"] for f in result["findings"]]
    adjustments = result["meta"].get("score_adjustments", [])

    assert "unilateral_price_increase" in rule_ids
    assert "service_suspension_right" in rule_ids
    assert "termination_for_convenience_counterparty" in rule_ids

    assert any(
        adj.get("type") == "compound_risk"
        and adj.get("rule_id") == "commercial_control_cluster"
        and adj.get("effect") == 2
        for adj in adjustments
    )

    assert result["risk_score"] == 14
