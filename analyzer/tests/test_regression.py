# analyzer/tests/test_regression.py

import pytest
from analyzer.tests.regression_cases import REGRESSION_CASES

# We will use the stable wrapper you added in analyzer/scorer.py
from analyzer.scorer import score_text


def _detected_labels(text: str) -> set[str]:
    """
    Your analyzer returns a dict like:
      {"risk_score": int, "severity": str, "flags": [...]}

    flags can be either:
      - list[str]  e.g. ["unlimited liability", "indemnify"]
      - list[dict] e.g. [{"label": "unlimited liability", ...}, ...]
    """
    result = score_text(text)

    if not isinstance(result, dict):
        raise TypeError(f"Expected dict from score_text, got {type(result)} -> {result}")

    flags = result.get("flags", [])

    # flags: ["x", ...]
    if isinstance(flags, list) and (not flags or isinstance(flags[0], str)):
        return set(map(str, flags))

    # flags: [{"label": "..."} ...] or [{"name": "..."} ...]
    if isinstance(flags, list) and flags and isinstance(flags[0], dict):
        labels = []
        for f in flags:
            if not isinstance(f, dict):
                continue
            for key in ("label", "name", "type"):
                if f.get(key):
                    labels.append(f[key])
                    break
        return set(map(str, labels))

    raise TypeError(f"Unexpected flags type/shape: {type(flags)} -> {flags}")


@pytest.mark.parametrize("case", REGRESSION_CASES)
def test_regression_case(case):
    text = case["text"]
    must_match = set(case.get("must_match", []))
    must_not_match = set(case.get("must_not_match", []))

    detected = _detected_labels(text)

    missing = must_match - detected
    unexpected = must_not_match & detected

    assert not missing, (
        f"Missing expected labels: {missing}\n"
        f"Text: {text}\n"
        f"Detected: {sorted(detected)}"
    )
    assert not unexpected, (
        f"Unexpected labels present: {unexpected}\n"
        f"Text: {text}\n"
        f"Detected: {sorted(detected)}"
    )
{
    "text": "The agreement may be terminated upon thirty days written notice.",
    "must_match": [],
    "must_not_match": ["termination without notice"]
},
