# analyzer/scorer.py

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Tuple, Union

from analyzer.rules import RISK_RULES


def _iter_rules(rules_obj) -> Iterable[Tuple[str, int, List[str]]]:
    """
    Normalize various possible RISK_RULES shapes into:
      (label: str, weight: int, patterns: list[str])

    Supported shapes:
    1) List/Tuple entries:
       - (label, weight, patterns)
       - (label, weight, patterns, anything_else...)
    2) Dict entries:
       - {"label": ..., "weight": ..., "patterns": [...]}
       - {"name": ..., "weight": ..., "regex": [...]}
    3) Dict mapping:
       - {"unlimited liability": [pattern1, pattern2], ...}
       - {"unlimited liability": {"weight": 5, "patterns": [...]}, ...}
       - {"unlimited liability": (5, [patterns...]), ...}
    """

    # Case 3: mapping dict
    if isinstance(rules_obj, dict):
        for label, val in rules_obj.items():
            if isinstance(val, dict):
                weight = int(val.get("weight", 1))
                patterns = (
                    val.get("patterns")
                    or val.get("regex")
                    or val.get("regexes")
                    or val.get("patterns_regex")
                    or []
                )
                if not isinstance(patterns, list):
                    patterns = list(patterns)
                yield (str(label), weight, [str(p) for p in patterns])
                continue

            if isinstance(val, tuple) and len(val) >= 2:
                weight = int(val[0])
                patterns = val[1]
                if not isinstance(patterns, list):
                    patterns = list(patterns)
                yield (str(label), weight, [str(p) for p in patterns])
                continue

            # assume val is patterns list
            patterns = val
            if not isinstance(patterns, list):
                patterns = list(patterns)
            yield (str(label), 1, [str(p) for p in patterns])
        return

    # Case 1/2: list/tuple of entries
    if isinstance(rules_obj, (list, tuple)):
        for entry in rules_obj:
            # Case 2: dict entry
            if isinstance(entry, dict):
                label = entry.get("label") or entry.get("name") or entry.get("type")
                if not label:
                    continue
                weight = int(entry.get("weight", 1))
                patterns = (
                    entry.get("patterns")
                    or entry.get("regex")
                    or entry.get("regexes")
                    or []
                )
                if not isinstance(patterns, list):
                    patterns = list(patterns)
                yield (str(label), weight, [str(p) for p in patterns])
                continue

            # Case 1: tuple/list entry
            if isinstance(entry, (list, tuple)) and len(entry) >= 3:
                label = str(entry[0])
                weight = int(entry[1])
                patterns = entry[2]
                if not isinstance(patterns, list):
                    patterns = list(patterns)
                yield (label, weight, [str(p) for p in patterns])
                continue

        return

    raise TypeError(f"Unsupported RISK_RULES type: {type(rules_obj)}")


# Precompile regex patterns once for speed + consistency
_COMPILED_RULES: List[Tuple[str, int, List[re.Pattern]]] = []
for label, weight, patterns in _iter_rules(RISK_RULES):
    compiled = [re.compile(p, flags=re.IGNORECASE | re.DOTALL) for p in patterns]
    _COMPILED_RULES.append((label, weight, compiled))


def score_contract(text: str) -> Dict[str, Any]:
    """
    Stable scoring contract:
      {
        "risk_score": int,
        "severity": "LOW" | "MEDIUM" | "HIGH",
        "flags": list[str]   # rule labels
      }
    """
    if not isinstance(text, str):
        text = str(text or "")

    flags: List[str] = []
    risk_score = 0

    for label, weight, regexes in _COMPILED_RULES:
        if any(rx.search(text) for rx in regexes):
            flags.append(label)
            risk_score += weight

    if risk_score >= 10:
        severity = "HIGH"
    elif risk_score >= 5:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
    "risk_score": risk_score,
    "severity": severity,
    "flags": sorted(flags),
}

# --- Stable public entrypoint for regression tests ---
def score_text(text: str):
    return score_contract(text)











