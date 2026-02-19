# analyzer/tests/test_contract_shape.py

from analyzer.scorer import score_text


def test_score_contract_shape():
    result = score_text("Sample contract text.")

    assert isinstance(result, dict)

    assert "risk_score" in result
    assert "severity" in result
    assert "flags" in result

    assert isinstance(result["risk_score"], int)
    assert result["severity"] in {"LOW", "MEDIUM", "HIGH"}
    assert isinstance(result["flags"], list)
