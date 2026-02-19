# analyzer/tests/test_case_coverage.py

from collections import defaultdict
from analyzer.tests.regression_cases import REGRESSION_CASES


def test_each_label_has_positive_and_negative_cases():
    """
    Enforces:
      - Every rule label must appear at least once in must_match
      - Every rule label must appear at least once in must_not_match
    """

    pos = defaultdict(int)
    neg = defaultdict(int)

    for case in REGRESSION_CASES:
        for label in case.get("must_match", []):
            pos[label] += 1
        for label in case.get("must_not_match", []):
            neg[label] += 1

    all_labels = sorted(set(pos.keys()) | set(neg.keys()))

    missing_pos = [l for l in all_labels if pos[l] == 0]
    missing_neg = [l for l in all_labels if neg[l] == 0]

    assert not missing_pos, f"Labels missing POSITIVE test cases: {missing_pos}"
    assert not missing_neg, f"Labels missing NEGATIVE test cases: {missing_neg}"
