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

_RENEWAL_RULE_IDS = {
    "auto_renewal_silent",
    "renewal_notice_window_pressure",
    "renewal_long_commitment",
}

_RENEWAL_PRICE_RULE_IDS = {
    "renewal_price_increase_on_renewal",
    "unilateral_price_increase",
}

_VARIATION_RULE_IDS = {
    "unilateral_amendment_policy_reference",
    "unilateral_price_increase",
}

_LIMITED_EXIT_RULE_IDS = {
    "termination_assistance_exit_dependency",
    "auto_renewal_silent",
    "renewal_notice_window_pressure",
    "renewal_long_commitment",
}

_INDEMNITY_RULE_IDS = {
    "indemnity_broad",
    "indemnity_one_way",
}

_WEAK_LIABILITY_PROTECTION_RULE_IDS = {
    "liability_cap_missing_or_unclear",
    "liability_super_cap_carveout",
    "liability_consequential_exclusion",
}

_JURISDICTION_RULE_IDS = {
    "governing_law_foreign_or_unfamiliar",
    "jurisdiction_exclusive_foreign_forum",
    "jurisdiction_non_exclusive_forum",
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
    if matched_material_dispute:
        effect = 0
        if calibrated_score < 6:
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


def _clean_extracted_location(value: str) -> str:
    cleaned = _normalize_ws(value)
    cleaned = re.sub(
        r"\s+(?:under|in accordance with|pursuant to|for any dispute|for all disputes|and the parties|and any dispute|and all disputes)\b.*$",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = cleaned.strip(" ,.;:")
    cleaned = re.sub(r"^(?:the\s+)?", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def _extract_jurisdiction_location(rule_id: str, matched_text: str) -> Optional[str]:
    patterns: List[Tuple[str, Optional[str]]] = []

    if rule_id == "governing_law_foreign_or_unfamiliar":
        patterns = [
            (r"governed\s+by\s+the\s+laws\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
            (r"governing\s+law\s+shall\s+be\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
        ]
    elif rule_id == "jurisdiction_exclusive_foreign_forum":
        patterns = [
            (
                r"exclusive\s+jurisdiction\s+of\s+the\s+courts?\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})",
                "courts",
            ),
            (
                r"submit\s+to\s+the\s+exclusive\s+jurisdiction\s+of\s+the\s+courts?\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})",
                "courts",
            ),
            (
                r"exclusive\s+forum\s+for\s+any\s+dispute\b.{0,80}\b(?:shall\s+be|is)\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})",
                None,
            ),
        ]
    elif rule_id == "jurisdiction_non_exclusive_forum":
        patterns = [
            (
                r"courts?\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})\s+shall\s+have\s+non-?exclusive\s+jurisdiction",
                "courts",
            ),
            (
                r"submit\s+to\s+the\s+non-?exclusive\s+jurisdiction\s+of\s+the\s+courts?\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})",
                "courts",
            ),
        ]
    elif rule_id == "arbitration_forum_or_seat":
        patterns = [
            (r"seat\s+of\s+arbitration(?:\s+shall\s+be|\s+is)?\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
            (r"arbitration\b.{0,100}\bseat(?:ed)?\s+in\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
            (r"arbitration\b.{0,100}\bvenue\s+(?:shall\s+be|is)?\s*(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
        ]
    elif rule_id == "venue_burden_foreign_court":
        patterns = [
            (r"venue\s+for\s+any\s+dispute\b.{0,80}\b(?:shall\s+be|is)\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})", None),
            (
                r"(?:shall\s+be\s+brought|must\s+be\s+brought)\b.{0,120}\bin\s+the\s+courts?\s+of\s+(?P<loc>[A-Za-z][A-Za-z\s,&-]{1,80})",
                "courts",
            ),
        ]

    for pattern, suffix in patterns:
        match = re.search(pattern, matched_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            continue
        location = _clean_extracted_location(match.group("loc"))
        if not location:
            continue
        if suffix == "courts" and "court" not in location.lower():
            return f"{location} courts"
        return location

    return None


def _dominant_document_geography(text: str) -> Optional[str]:
    lowered = text.lower()
    uk_signals = [
        r"\bengland and wales\b",
        r"\bengland\b",
        r"\bwales\b",
        r"\bunited kingdom\b",
        r"\buk\b",
        r"\blondon\b",
    ]
    uk_hits = sum(len(re.findall(pattern, lowered)) for pattern in uk_signals)
    if uk_hits >= 2 or re.search(r"\bengland and wales\b", lowered):
        return "uk"
    return None


def _mismatch_context_note(text: str, extracted_location: Optional[str]) -> Optional[str]:
    if not extracted_location:
        return None

    dominant_geo = _dominant_document_geography(text)
    if dominant_geo != "uk":
        return None

    location_lower = extracted_location.lower()
    uk_location_markers = ("england", "wales", "london", "uk", "united kingdom", "britain", "british")
    if any(marker in location_lower for marker in uk_location_markers):
        return None

    return "Selected forum appears different from the document's dominant geography."


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


def _combine_match_span(findings: List[Dict[str, Any]]) -> List[int]:
    spans = [f.get("match_span", [0, 0]) for f in findings if f.get("match_span")]
    starts = [int(span[0]) for span in spans if len(span) > 0]
    ends = [int(span[1]) for span in spans if len(span) > 1]
    if not starts or not ends:
        return [0, 0]
    return [min(starts), max(ends)]


def _combine_excerpt(findings: List[Dict[str, Any]], limit: int = 2) -> str:
    excerpts: List[str] = []
    for finding in findings:
        excerpt = _normalize_ws(str(finding.get("excerpt", "")))
        if excerpt and excerpt not in excerpts:
            excerpts.append(excerpt)
        if len(excerpts) >= limit:
            break
    return " | ".join(excerpts)


def _location_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    cleaned = value.lower()
    cleaned = re.sub(r"\bcourts?\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.;:")
    if "," in cleaned:
        tail = cleaned.split(",")[-1].strip()
        if tail:
            cleaned = tail
    return cleaned or None


def _derived_finding(
    *,
    rule_id: str,
    category: str,
    title: str,
    severity: int,
    weight: int,
    rationale: str,
    triggered_by: List[str],
    contributors: List[Dict[str, Any]],
) -> Dict[str, Any]:
    span = _combine_match_span(contributors)
    return {
        "rule_id": rule_id,
        "category": category,
        "title": title,
        "severity": severity,
        "weight": weight,
        "priority": 120,
        "rationale": rationale,
        "matched_pattern": "derived_cross_clause",
        "match_span": span,
        "matched_text": _combine_excerpt(contributors, limit=1),
        "matched_location": None,
        "context_note": None,
        "excerpt": _combine_excerpt(contributors),
        "tags": ["cross_clause", "derived_signal"],
        "triggered_by": triggered_by,
    }


def _build_cross_clause_findings(
    findings: List[Dict[str, Any]],
    matched_rule_ids: set[str],
    raw_matched_rule_ids: set[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    by_rule_id: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        by_rule_id.setdefault(str(finding.get("rule_id", "")), []).append(finding)

    cross_findings: List[Dict[str, Any]] = []
    cross_adjustments: List[Dict[str, Any]] = []

    matched_renewal = sorted(matched_rule_ids.intersection(_RENEWAL_RULE_IDS))
    matched_renewal_price = sorted(matched_rule_ids.intersection(_RENEWAL_PRICE_RULE_IDS))
    if matched_renewal and matched_renewal_price:
        triggered_by = matched_renewal + matched_renewal_price
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_lock_in = any(rid in {"renewal_notice_window_pressure", "renewal_long_commitment"} for rid in matched_renewal)
        effect = 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_renewal_price_lock_in",
                category="renewal",
                title="Renewal lock-in with price escalation",
                severity=4 if stronger_lock_in else 3,
                weight=effect,
                rationale="Renewal controls and pricing escalation language appear together, which may lock the business into a continued term while cost exposure increases.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_renewal_price_lock_in",
                "effect": effect,
                "reason": "Renewal lock-in combined with pricing escalation may weaken renewal leverage and expand forward cost exposure.",
                "triggered_by": triggered_by,
            }
        )

    matched_variation = sorted(matched_rule_ids.intersection(_VARIATION_RULE_IDS))
    matched_exit = sorted(matched_rule_ids.intersection(_LIMITED_EXIT_RULE_IDS))
    has_structural_variation = "unilateral_amendment_policy_reference" in matched_variation
    if matched_variation and matched_exit and (has_structural_variation or len(matched_exit) >= 2):
        triggered_by = matched_variation + matched_exit
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        cross_findings.append(
            _derived_finding(
                rule_id="cross_unilateral_variation_limited_exit",
                category="amendment",
                title="Unilateral variation with limited exit flexibility",
                severity=4,
                weight=2,
                rationale="The counterparty appears able to change operational or commercial terms while exit rights remain constrained, which can reduce practical leverage if the clause package moves against the customer.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_unilateral_variation_limited_exit",
                "effect": 2,
                "reason": "Variation rights paired with limited exit flexibility may create stronger commercial leverage than either clause family alone.",
                "triggered_by": triggered_by,
            }
        )

    matched_indemnity = sorted(matched_rule_ids.intersection(_INDEMNITY_RULE_IDS))
    matched_weak_liability = sorted(matched_rule_ids.intersection(_WEAK_LIABILITY_PROTECTION_RULE_IDS))
    if matched_indemnity and matched_weak_liability:
        triggered_by = matched_indemnity + matched_weak_liability
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        cross_findings.append(
            _derived_finding(
                rule_id="cross_indemnity_cap_gap",
                category="liability",
                title="Indemnity exposure with weak liability protection",
                severity=4,
                weight=2,
                rationale="Broad indemnity language appears alongside weak, unclear, or heavily carved-out liability protection, which may increase review priority before accepting the overall allocation of financial risk.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_indemnity_cap_gap",
                "effect": 2,
                "reason": "Broad indemnity obligations combined with weak liability protection can amplify downside exposure in a way that deserves consolidated review.",
                "triggered_by": triggered_by,
            }
        )

    jurisdiction_findings = [
        finding for finding in findings if str(finding.get("rule_id", "")) in _JURISDICTION_RULE_IDS
    ]
    jurisdiction_locations = {
        _location_key(str(finding.get("matched_location") or ""))
        for finding in jurisdiction_findings
        if _location_key(str(finding.get("matched_location") or ""))
    }
    has_context_mismatch = any(finding.get("context_note") for finding in jurisdiction_findings)
    has_venue_burden = "venue_burden_foreign_court" in raw_matched_rule_ids
    if has_context_mismatch or has_venue_burden or len(jurisdiction_locations) >= 2:
        triggered_by = sorted(
            {str(finding.get("rule_id", "")) for finding in jurisdiction_findings if str(finding.get("rule_id", ""))}
        )
        contributors = jurisdiction_findings[:3]
        if triggered_by:
            cross_findings.append(
                _derived_finding(
                    rule_id="cross_forum_burden_mismatch",
                    category="jurisdiction",
                    title="Dispute forum mismatch or venue burden",
                    severity=4,
                    weight=2,
                    rationale="The dispute forum package may create cross-border, mismatched, or operationally burdensome escalation routes, which can affect venue cost, enforcement planning, and negotiation confidence.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                )
            )
            cross_adjustments.append(
                {
                    "type": "compound_risk",
                    "rule_id": "cross_forum_burden_mismatch",
                    "effect": 2,
                    "reason": "A mismatch or burden across governing law, jurisdiction, arbitration, or venue can make dispute handling materially harder than a single clause would suggest on its own.",
                    "triggered_by": triggered_by,
                }
            )

    return cross_findings, cross_adjustments


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
        matched_text = _normalize_ws(scan_text[start:end])
        extraction_text = _excerpt(scan_text, start, end, window=140)
        matched_location = _extract_jurisdiction_location(rule["rule_id"], extraction_text)
        context_note = (
            _mismatch_context_note(scan_text, matched_location)
            if rule["category"] == "jurisdiction"
            else None
        )
        rationale = rule["rationale"]
        if context_note:
            rationale = f"{rationale} {context_note}"

        raw_findings.append(
            {
                "rule_id": rule["rule_id"],
                "category": rule["category"],
                "title": rule["title"],
                "severity": rule["severity"],
                "weight": rule["weight"],
                "priority": rule["priority"],
                "rationale": rationale,
                "matched_pattern": pattern_str,
                "match_span": [start, end],
                "matched_text": matched_text,
                "matched_location": matched_location,
                "context_note": context_note,
                "excerpt": extraction_text,
                "tags": rule["tags"],
            }
        )

    deduped_findings, overlap_suppressions = _dedupe_findings(raw_findings)
    raw_matched_rule_ids: set[str] = {str(f["rule_id"]) for f in raw_findings}
    matched_rule_ids: set[str] = {str(f["rule_id"]) for f in deduped_findings}
    raw_risk_score = sum(int(f["weight"]) for f in deduped_findings)

    adjusted_risk_score, score_adjustments = _apply_mitigation_and_conflict_adjustments(
        matched_rule_ids, raw_risk_score
    )

    cross_findings, cross_adjustments = _build_cross_clause_findings(
        raw_findings,
        matched_rule_ids,
        raw_matched_rule_ids,
    )
    if cross_adjustments:
        adjusted_risk_score += sum(int(adj.get("effect", 0)) for adj in cross_adjustments)
        score_adjustments.extend(cross_adjustments)
    if cross_findings:
        deduped_findings.extend(cross_findings)
        matched_rule_ids = {str(f["rule_id"]) for f in deduped_findings}

    flags: List[str] = [_display_flag(f) for f in deduped_findings]

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
                "matched_location": f.get("matched_location"),
                "context_note": f.get("context_note"),
            }
            for f in prioritized_findings[:3]
        ]
        if overlap_suppressions:
            result["meta"]["overlap_suppressions"] = overlap_suppressions

    return result


def score_text(text: str):
    return score_contract(text)
