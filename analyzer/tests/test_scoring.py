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
