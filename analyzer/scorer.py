from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from analyzer.rules import (
    RISK_RULE_OBJECTS,
    RULESET_VERSION,
    RULE_NEGATIVE_PATTERNS,
    RULE_PRIORITIES,
    RULE_TAGS,
)

MAX_SCAN_CHARS = 60_000


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def _excerpt(text: str, start: int, end: int, window: int = 90) -> str:
    n = len(text)
    left = max(0, start - window)
    right = min(n, end + window)
    return _normalize_ws(text[left:right])


def _word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text or ""))


def _scan_view(text: str) -> str:
    if not text:
        return ""
    if len(text) <= MAX_SCAN_CHARS:
        return text
    return text[:MAX_SCAN_CHARS]


def _clamp_float(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    if v < lo:
        return lo
    if v > hi:
        return hi
    return v


_COMPILED_OBJECT_RULES: List[Dict[str, Any]] = []

for rule in RISK_RULE_OBJECTS:
    compiled_pairs: List[Tuple[str, re.Pattern]] = [
        (p, re.compile(p, flags=re.IGNORECASE | re.DOTALL))
        for p in rule.patterns
    ]

    negative_pairs: List[Tuple[str, re.Pattern]] = [
        (p, re.compile(p, flags=re.IGNORECASE | re.DOTALL))
        for p in RULE_NEGATIVE_PATTERNS.get(rule.id, [])
    ]

    _COMPILED_OBJECT_RULES.append(
        {
            "rule_id": rule.id,
            "category": rule.category,
            "title": rule.title,
            "severity": int(rule.severity),
            "weight": int(rule.weight),
            "rationale": rule.rationale,
            "patterns": compiled_pairs,
            "negative_patterns": negative_pairs,
            "priority": int(RULE_PRIORITIES.get(rule.id, rule.weight)),
            "tags": list(RULE_TAGS.get(rule.id, [])),
            "min_matches": int(getattr(rule, "min_matches", 1)),
            "max_span_chars": int(getattr(rule, "max_span_chars", 120)),
        }
    )

_MAX_POSSIBLE_SCORE: int = sum(max(0, int(r.weight)) for r in RISK_RULE_OBJECTS)

_MATERIAL_DISPUTE_FORUM_RULES = {
    "governing_law_foreign_or_unfamiliar",
    "jurisdiction_exclusive_foreign_forum",
    "arbitration_forum_or_seat",
    "venue_burden_foreign_court",
}


def _normalized_score(raw_score: int) -> int:
    if _MAX_POSSIBLE_SCORE <= 0:
        return 0
    pct = int(round((raw_score / _MAX_POSSIBLE_SCORE) * 100))
    if pct < 0:
        return 0
    if pct > 100:
        return 100
    return pct


def _calibrate_minimum_exposure(
    adjusted_score: int,
    matched_rule_ids: set[str],
) -> Tuple[int, List[Dict[str, Any]]]:
    calibrated_score = adjusted_score
    adjustments: List[Dict[str, Any]] = []

    matched_material_dispute = sorted(_MATERIAL_DISPUTE_FORUM_RULES.intersection(matched_rule_ids))
    if matched_material_dispute and calibrated_score < 6:
        effect = 6 - calibrated_score
        calibrated_score = 6
        adjustments.append(
            {
                "type": "minimum_exposure_floor",
                "rule_id": "material_dispute_forum_floor",
                "effect": effect,
                "reason": "A governing-law, jurisdiction, arbitration, or venue burden signal should remain review-elevating even when it appears as a single concentrated clause cluster.",
                "triggered_by": matched_material_dispute,
            }
        )

    return calibrated_score, adjustments


def _calibrated_normalized_score(
    adjusted_score: int,
    findings: List[Dict[str, Any]],
) -> int:
    base_score = _normalized_score(adjusted_score)
    if not findings:
        return base_score

    matched_rule_ids = {str(f.get("rule_id", "")) for f in findings}
    highest_finding_severity = max(int(f.get("severity", 0)) for f in findings)

    if matched_rule_ids.intersection(_MATERIAL_DISPUTE_FORUM_RULES):
        return max(base_score, 28)

    if highest_finding_severity >= 5:
        return max(base_score, 22)

    return base_score


def _find_first_match(
    compiled_pairs: List[Tuple[str, re.Pattern]],
    text: str,
) -> Optional[Tuple[str, re.Match]]:
    for pattern_str, rx in compiled_pairs:
        m = rx.search(text)
        if m:
            return pattern_str, m
    return None


def _has_negative_override(
    negative_pairs: List[Tuple[str, re.Pattern]],
    text: str,
) -> Optional[str]:
    for pattern_str, rx in negative_pairs:
        if rx.search(text):
            return pattern_str
    return None


def _spans_overlap(
    a_start: int,
    a_end: int,
    b_start: int,
    b_end: int,
) -> bool:
    return max(a_start, b_start) < min(a_end, b_end)


def _spans_related(
    a_start: int,
    a_end: int,
    b_start: int,
    b_end: int,
    max_gap: int = 220,
) -> bool:
    if _spans_overlap(a_start, a_end, b_start, b_end):
        return True
    if a_end <= b_start:
        return (b_start - a_end) <= max_gap
    if b_end <= a_start:
        return (a_start - b_end) <= max_gap
    return False


def _finding_rank_key(f: Dict[str, Any]) -> Tuple[int, int, int, int]:
    span = f.get("match_span", [0, 0])
    start = int(span[0]) if len(span) > 0 else 0
    end = int(span[1]) if len(span) > 1 else 0
    width = max(0, end - start)

    return (
        int(f.get("priority", 1)),
        int(f.get("severity", 1)),
        int(f.get("weight", 0)),
        -width,
    )


def _dedupe_findings(
    findings: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not findings:
        return [], []

    kept: List[Dict[str, Any]] = []
    suppressed: List[Dict[str, Any]] = []

    ranked = sorted(findings, key=_finding_rank_key, reverse=True)

    for candidate in ranked:
        c_span = candidate.get("match_span", [0, 0])
        c_start = int(c_span[0]) if len(c_span) > 0 else 0
        c_end = int(c_span[1]) if len(c_span) > 1 else 0
        c_cat = str(candidate.get("category", ""))

        duplicate_of_existing = False

        for existing in kept:
            e_span = existing.get("match_span", [0, 0])
            e_start = int(e_span[0]) if len(e_span) > 0 else 0
            e_end = int(e_span[1]) if len(e_span) > 1 else 0
            e_cat = str(existing.get("category", ""))

            if c_cat == e_cat and _spans_overlap(c_start, c_end, e_start, e_end):
                duplicate_of_existing = True
                suppressed.append(
                    {
                        "rule_id": candidate.get("rule_id"),
                        "title": candidate.get("title"),
                        "suppressed_by_rule_id": existing.get("rule_id"),
                        "reason": "overlapping_evidence_same_category",
                    }
                )
                break

            if (
                c_cat == "jurisdiction"
                and e_cat == "jurisdiction"
                and _spans_related(c_start, c_end, e_start, e_end)
            ):
                duplicate_of_existing = True
                suppressed.append(
                    {
                        "rule_id": candidate.get("rule_id"),
                        "title": candidate.get("title"),
                        "suppressed_by_rule_id": existing.get("rule_id"),
                        "reason": "related_jurisdiction_clause_cluster",
                    }
                )
                break

        if not duplicate_of_existing:
            kept.append(candidate)

    kept.sort(
        key=lambda f: (
            -int(f.get("priority", 1)),
            -int(f.get("severity", 1)),
            -int(f.get("weight", 0)),
            str(f.get("title", "")),
        )
    )

    return kept, suppressed


def _apply_mitigation_and_conflict_adjustments(
    matched_rule_ids: set[str],
    raw_score: int,
) -> Tuple[int, List[Dict[str, Any]]]:
    adjusted_score = raw_score
    adjustments: List[Dict[str, Any]] = []

    if "liability_cap_present" in matched_rule_ids:
        liability_risk_present = any(
            rid in matched_rule_ids
            for rid in {
                "liability_unlimited",
                "liability_cap_missing_or_unclear",
                "liability_super_cap_carveout",
                "indemnity_broad",
                "indemnity_one_way",
                "liability_consequential_exclusion",
            }
        )
        if liability_risk_present:
            adjusted_score = max(0, adjusted_score - 2)
            adjustments.append(
                {
                    "type": "mitigation",
                    "rule_id": "liability_cap_present",
                    "effect": -2,
                    "reason": "Liability cap may reduce some exposure, but should not eliminate carve-out or related liability risk.",
                }
            )

    if (
        "liability_cap_present" in matched_rule_ids
        and "liability_super_cap_carveout" in matched_rule_ids
    ):
        adjusted_score = max(adjusted_score, 3)
        adjustments.append(
            {
                "type": "contradiction",
                "rule_id": "liability_super_cap_carveout",
                "effect": 0,
                "reason": "Cap carve-out preserves residual liability exposure despite cap language.",
            }
        )

    if "liability_consequential_exclusion" in matched_rule_ids:
        adjusted_score = max(0, adjusted_score - 1)
        adjustments.append(
            {
                "type": "mitigation",
                "rule_id": "liability_consequential_exclusion",
                "effect": -1,
                "reason": "Consequential damages exclusion is treated as a mild mitigating liability structure term.",
            }
        )

    liability_exposure_rules = {
        "liability_unlimited",
        "liability_cap_missing_or_unclear",
        "liability_super_cap_carveout",
    }
    indemnity_rules = {
        "indemnity_broad",
        "indemnity_one_way",
    }

    matched_liability_exposure = liability_exposure_rules.intersection(matched_rule_ids)
    matched_indemnity = indemnity_rules.intersection(matched_rule_ids)

    if matched_liability_exposure and matched_indemnity:
        adjusted_score += 2
        adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "liability_indemnity_cluster",
                "effect": 2,
                "reason": "Indemnity obligations combined with uncapped, unclear, or carve-out liability language may materially amplify financial exposure.",
                "triggered_by": sorted(matched_liability_exposure.union(matched_indemnity)),
            }
        )

    commercial_control_cluster = {
        "unilateral_price_increase",
        "service_suspension_right",
        "termination_for_convenience_counterparty",
    }

    matched_control_rules = commercial_control_cluster.intersection(matched_rule_ids)
    if len(matched_control_rules) >= 2:
        adjusted_score += 2
        adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "commercial_control_cluster",
                "effect": 2,
                "reason": "Multiple unilateral commercial control rights may combine to create stronger counterparty leverage than any single clause in isolation.",
                "triggered_by": sorted(matched_control_rules),
            }
        )

    return adjusted_score, adjustments


def _derive_severity(score: int) -> str:
    if score >= 12:
        return "HIGH"
    if score >= 5:
        return "MEDIUM"
    return "LOW"


def _display_flag(finding: Dict[str, Any]) -> str:
    rule_id = str(finding.get("rule_id", ""))
    matched_text = str(finding.get("matched_text", "")).lower()

    if rule_id == "termination_for_convenience_counterparty" and "without notice" in matched_text:
        return "termination without notice"

    if rule_id == "unilateral_price_increase":
        return "unilateral price increase right"

    return str(finding.get("title", "")).lower()


def score_contract(
    text: str,
    *,
    include_findings: bool = True,
    include_meta: bool = True,
) -> Dict[str, Any]:
    original_text = text or ""
    scan_text = _scan_view(original_text)
    raw_findings: List[Dict[str, Any]] = []
    suppressed_rules: List[Dict[str, Any]] = []

    for rule in _COMPILED_OBJECT_RULES:
        negative_hit = _has_negative_override(rule["negative_patterns"], scan_text)
        if negative_hit:
            suppressed_rules.append(
                {
                    "rule_id": rule["rule_id"],
                    "title": rule["title"],
                    "reason": "negative_pattern_override",
                    "pattern": negative_hit,
                }
            )
            continue

        first_match = _find_first_match(rule["patterns"], scan_text)
        if not first_match:
            continue

        pattern_str, match_obj = first_match
        start, end = match_obj.span()

        raw_findings.append(
            {
                "rule_id": rule["rule_id"],
                "category": rule["category"],
                "title": rule["title"],
                "severity": rule["severity"],
                "weight": rule["weight"],
                "priority": rule["priority"],
                "rationale": rule["rationale"],
                "matched_pattern": pattern_str,
                "match_span": [start, end],
                "matched_text": _normalize_ws(scan_text[start:end]),
                "excerpt": _excerpt(scan_text, start, end),
                "tags": rule["tags"],
            }
        )

    deduped_findings, overlap_suppressions = _dedupe_findings(raw_findings)

    matched_rule_ids: set[str] = {str(f["rule_id"]) for f in deduped_findings}
    flags: List[str] = [_display_flag(f) for f in deduped_findings]
    raw_risk_score = sum(int(f["weight"]) for f in deduped_findings)

    adjusted_risk_score, score_adjustments = _apply_mitigation_and_conflict_adjustments(
        matched_rule_ids, raw_risk_score
    )

    if "termination_for_convenience_counterparty" in matched_rule_ids:
        adjusted_risk_score = max(adjusted_risk_score, 5)

    if "unilateral_price_increase" in matched_rule_ids:
        adjusted_risk_score = max(adjusted_risk_score, 5)

    adjusted_risk_score, minimum_exposure_adjustments = _calibrate_minimum_exposure(
        adjusted_risk_score,
        matched_rule_ids,
    )
    if minimum_exposure_adjustments:
        score_adjustments.extend(minimum_exposure_adjustments)

    contradiction_count = sum(
        1 for adj in score_adjustments if adj.get("type") == "contradiction"
    )
    suppressed_count = len(suppressed_rules)

    severity = _derive_severity(adjusted_risk_score)

    prioritized_findings = sorted(
        deduped_findings,
        key=lambda f: (
            -int(f.get("severity", 0)),
            -int(f.get("weight", 0)),
            str(f.get("title", "")),
        ),
    )

    result: Dict[str, Any] = {
        "risk_score": adjusted_risk_score,
        "severity": severity,
        "flags": sorted(set(flags)),
    }

    if include_findings:
        result["findings"] = prioritized_findings

    if include_meta:
        wc = _word_count(original_text)
        result["meta"] = {
            "confidence": _clamp_float(1.0 if wc > 0 else 0.0),
            "risk_density": round(adjusted_risk_score / max(wc, 1), 4),
            "ruleset_version": RULESET_VERSION,
            "score_adjustments": score_adjustments,
            "matched_rule_count": len(deduped_findings),
            "suppressed_rule_count": suppressed_count,
            "normalized_score": _calibrated_normalized_score(adjusted_risk_score, deduped_findings),
            "raw_risk_score": raw_risk_score,
            "contradiction_count": contradiction_count,
            "scan_char_limit": MAX_SCAN_CHARS,
            "scanned_chars": min(len(original_text), MAX_SCAN_CHARS),
            "scan_truncated": len(original_text) > MAX_SCAN_CHARS,
        }
        result["meta"]["top_risks"] = [
            {
                "rule_id": f.get("rule_id"),
                "title": f.get("title"),
                "category": f.get("category"),
                "severity": f.get("severity"),
                "weight": f.get("weight"),
            }
            for f in prioritized_findings[:3]
        ]
        if overlap_suppressions:
            result["meta"]["overlap_suppressions"] = overlap_suppressions

    return result


def score_text(text: str):
    return score_contract(text)
