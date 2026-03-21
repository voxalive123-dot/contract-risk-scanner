import pytest

from analyzer.risk_schema import RiskRule


def test_risk_rule_valid_construction():
    rule = RiskRule(
        id="liability_unlimited",
        category="liability",
        title="Unlimited liability",
        severity=5,
        weight=5,
        rationale="No cap on liability exposes the party to unbounded losses.",
        patterns=[r"\bunlimited\s+liabilit(y|ies)\b"],
    )
    assert rule.id == "liability_unlimited"
    assert rule.severity == 5
    assert rule.patterns == [r"\bunlimited\s+liabilit(y|ies)\b"]


@pytest.mark.parametrize("bad_id", ["", "   "])
def test_risk_rule_rejects_empty_id(bad_id):
    with pytest.raises(ValueError):
        RiskRule(
            id=bad_id,
            category="liability",
            title="Unlimited liability",
            severity=5,
            weight=5,
            rationale="x",
            patterns=[r"\bfoo\b"],
        )


@pytest.mark.parametrize("bad_category", ["", "   "])
def test_risk_rule_rejects_empty_category(bad_category):
    with pytest.raises(ValueError):
        RiskRule(
            id="liability_unlimited",
            category=bad_category,
            title="Unlimited liability",
            severity=5,
            weight=5,
            rationale="x",
            patterns=[r"\bfoo\b"],
        )


@pytest.mark.parametrize("bad_title", ["", "   "])
def test_risk_rule_rejects_empty_title(bad_title):
    with pytest.raises(ValueError):
        RiskRule(
            id="liability_unlimited",
            category="liability",
            title=bad_title,
            severity=5,
            weight=5,
            rationale="x",
            patterns=[r"\bfoo\b"],
        )


@pytest.mark.parametrize("bad_severity", [0, 6, -1, 999])
def test_risk_rule_rejects_out_of_range_severity(bad_severity):
    with pytest.raises(ValueError):
        RiskRule(
            id="liability_unlimited",
            category="liability",
            title="Unlimited liability",
            severity=bad_severity,
            weight=5,
            rationale="x",
            patterns=[r"\bfoo\b"],
        )


@pytest.mark.parametrize("bad_weight", [-1, -999])
def test_risk_rule_rejects_negative_weight(bad_weight):
    with pytest.raises(ValueError):
        RiskRule(
            id="liability_unlimited",
            category="liability",
            title="Unlimited liability",
            severity=5,
            weight=bad_weight,
            rationale="x",
            patterns=[r"\bfoo\b"],
        )


@pytest.mark.parametrize("bad_patterns", [None, [], ["", "   "], [123], ["ok", 456]])
def test_risk_rule_rejects_invalid_patterns(bad_patterns):
    with pytest.raises(ValueError):
        RiskRule(
            id="liability_unlimited",
            category="liability",
            title="Unlimited liability",
            severity=5,
            weight=5,
            rationale="x",
            patterns=bad_patterns,  # type: ignore[arg-type]
        )