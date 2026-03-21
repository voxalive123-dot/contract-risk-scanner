# analyzer/tests/test_rules_regression.py
"""
Regression tests for regex-based risk rules.

Goal:
- MUST_MATCH cases must trigger their target rule label.
- MUST_NOT_MATCH cases must NOT trigger their target rule label.

This file is intentionally "schema tolerant":
- Works whether RISK_RULES entries are dicts (your current schema) or tuples.
- Adds label normalization + aliasing so tests don't break on hyphen/space/case differences.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import pytest

from analyzer.rules import RISK_RULES


# ----------------------------
# Helpers: schema + label normalization
# ----------------------------

def _norm_label(s: str) -> str:
    """
    Canonical form for label matching:
    - lowercase
    - convert '_' to '-'
    - collapse whitespace
    - strip punctuation-ish separators to single '-'
    """
    s = (s or "").strip().lower()
    s = s.replace("_", "-")
    s = re.sub(r"\s+", " ", s)
    # turn spaces/slashes into hyphens
    s = re.sub(r"[ /]+", "-", s)
    # collapse multiple hyphens
    s = re.sub(r"-{2,}", "-", s)
    return s


def _extract_rule(rule: Any) -> Tuple[str, int, List[str]]:
    """
    Return (label, weight, patterns) from either:
      - dict: {"label":..., "weight":..., "patterns":[...]}
      - tuple/list: (label, weight, [patterns])
    """
    if isinstance(rule, dict):
        label = str(rule.get("label", "")).strip()
        weight = int(rule.get("weight", 0))
        patterns = list(rule.get("patterns", []) or [])
        return label, weight, patterns

    if isinstance(rule, (tuple, list)) and len(rule) >= 3:
        label = str(rule[0]).strip()
        weight = int(rule[1])
        patterns = list(rule[2] or [])
        return label, weight, patterns

    raise TypeError(f"Unsupported rule format: {type(rule)} -> {rule!r}")


def _build_label_index(rules: Sequence[Any]) -> Tuple[Dict[str, str], List[str]]:
    """
    Builds a lookup dict from normalized label -> actual label as defined in rules.py
    """
    actual_labels: List[str] = []
    index: Dict[str, str] = {}
    for r in rules:
        label, _weight, _patterns = _extract_rule(r)
        if not label:
            continue
        actual_labels.append(label)
        index[_norm_label(label)] = label
    return index, sorted(actual_labels)


# Aliases: left side = what tests might say, right side = what rules likely use.
# You can extend this safely without touching the rule engine.
LABEL_ALIASES: Dict[str, str] = {
    # common variants
    "auto-renew": "auto renewal",
    "auto renew": "auto renewal",
    "auto-renewal": "auto renewal",
    "auto renewal": "auto renewal",

    "indemnify": "indemnify",
    "indemnification": "indemnify",
    "indemnity": "indemnify",

    "non-solicit": "non solicitation",
    "non solicit": "non solicitation",
    "non-solicitation": "non solicitation",

    "non-compete": "non compete",
    "noncompete": "non compete",

    "termination w/o notice": "termination without notice",
    "termination without notice": "termination without notice",
    "terminate without notice": "termination without notice",
}


def _resolve_label(requested: str, label_index: Dict[str, str], all_labels: List[str]) -> str:
    """
    Resolve a test label to the exact label used in rules.py, using:
      1) exact match
      2) normalized match
      3) alias mapping (normalized)
    """
    requested = (requested or "").strip()
    if not requested:
        raise AssertionError("Empty label in regression test case.")

    # 1) exact label
    if requested in all_labels:
        return requested

    # 2) normalized label
    n = _norm_label(requested)
    if n in label_index:
        return label_index[n]

    # 3) alias
    aliased = LABEL_ALIASES.get(n) or LABEL_ALIASES.get(requested)  # support both raw and normalized keys
    if aliased:
        na = _norm_label(aliased)
        if na in label_index:
            return label_index[na]

    # If we still can't resolve, show useful debugging output.
    suggestions = ", ".join(all_labels[:30]) + (" ..." if len(all_labels) > 30 else "")
    raise AssertionError(
        f"Unknown risk label in test: {requested!r}\n"
        f"Available rule labels include: {suggestions}\n"
        f"Tip: update the test label to match rules.py OR add an alias in LABEL_ALIASES."
    )


# ----------------------------
# Compile rules once for speed + determinism
# ----------------------------

def _compiled_rules() -> List[Tuple[str, int, List[re.Pattern]]]:
    """
    Compile all regex patterns once.
    Flags:
      - IGNORECASE: contracts vary in casing
      - MULTILINE: clauses often span lines
      - DOTALL: allow '.' to cross newlines where patterns need it
    """
    compiled: List[Tuple[str, int, List[re.Pattern]]] = []
    for rule in RISK_RULES:
        label, weight, patterns = _extract_rule(rule)
        compiled_patterns: List[re.Pattern] = []
        for p in patterns:
            compiled_patterns.append(re.compile(p, re.IGNORECASE | re.MULTILINE | re.DOTALL))
        compiled.append((label, weight, compiled_patterns))
    return compiled


COMPILED = _compiled_rules()
LABEL_INDEX, ALL_LABELS = _build_label_index(RISK_RULES)


def _match_label(text: str, target_label: str) -> bool:
    """
    Return True if any compiled regex for target label matches text.
    """
    for label, _weight, patterns in COMPILED:
        if label == target_label:
            return any(rx.search(text) for rx in patterns)
    raise AssertionError(f"Resolved label {target_label!r} not found in compiled rules (unexpected).")


# ----------------------------
# Load regression cases
# ----------------------------

# If you have analyzer/tests/regression_cases.py, we’ll auto-use it.
# Expected format: MUST_MATCH / MUST_NOT_MATCH lists of tuples: (label, text)
try:
    from analyzer.tests.regression_cases import MUST_MATCH as EXT_MUST_MATCH  # type: ignore
    from analyzer.tests.regression_cases import MUST_NOT_MATCH as EXT_MUST_NOT_MATCH  # type: ignore

    MUST_MATCH: List[Tuple[str, str]] = list(EXT_MUST_MATCH)
    MUST_NOT_MATCH: List[Tuple[str, str]] = list(EXT_MUST_NOT_MATCH)
except Exception:
    # Fallback examples (edit as needed)
    MUST_MATCH = [
        ("unlimited liability", "The Supplier's liability shall be unlimited."),
    ]
    MUST_NOT_MATCH = [
        ("unlimited liability", "The Supplier's liability shall be capped at £100,000."),
    ]


# ----------------------------
# Tests
# ----------------------------

@pytest.mark.parametrize("label,text", MUST_MATCH)
def test_rules_must_match(label: str, text: str) -> None:
    resolved = _resolve_label(label, LABEL_INDEX, ALL_LABELS)
    assert _match_label(text, resolved), f"Expected match for {label!r} (resolved to {resolved!r})"


@pytest.mark.parametrize("label,text", MUST_NOT_MATCH)
def test_rules_must_not_match(label: str, text: str) -> None:
    resolved = _resolve_label(label, LABEL_INDEX, ALL_LABELS)
    assert not _match_label(text, resolved), f"Expected NO match for {label!r} (resolved to {resolved!r})"