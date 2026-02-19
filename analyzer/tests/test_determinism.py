# analyzer/tests/test_determinism.py

from analyzer.scorer import score_text


def test_score_is_deterministic():
    text = "Either party may terminate this agreement without notice."

    r1 = score_text(text)
    r2 = score_text(text)
    r3 = score_text(text)

    assert r1 == r2 == r3
