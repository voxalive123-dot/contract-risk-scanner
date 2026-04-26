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


def test_detect_exclusive_foreign_jurisdiction():
    text = "The parties submit to the exclusive jurisdiction of the courts of New York."
    result = score_contract(text)

    assert result["risk_score"] >= 6
    assert "exclusive foreign jurisdiction" in result["flags"]


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


def test_foreign_governing_law_alone_is_not_low_signal():
    text = "This agreement is governed by the laws of California."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert result["severity"] == "MEDIUM"
    assert result["risk_score"] >= 6
    assert result["meta"]["normalized_score"] >= 28
