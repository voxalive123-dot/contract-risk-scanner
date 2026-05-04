from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from decision_intelligence import apply_policy_to_payload
from analyzer.context_profiles import (
    SYNTHESIS_PATTERN_METADATA,
    build_context_profile_metadata,
)

from analyzer.rules import (
    RISK_RULE_OBJECTS,
    RULESET_VERSION,
    LABEL_ALIASES,
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
    "auto_renewal_notice_trap",
    "auto_renewal_hidden_cancellation_burden",
}

_RENEWAL_PRICE_RULE_IDS = {
    "renewal_price_increase_on_renewal",
}

_VARIATION_RULE_IDS = {
    "unilateral_amendment_policy_reference",
    "unilateral_price_increase",
    "unilateral_change_control_scope_terms",
}

_LIMITED_EXIT_RULE_IDS = {
    "termination_assistance_exit_dependency",
    "auto_renewal_silent",
    "renewal_notice_window_pressure",
    "renewal_long_commitment",
    "auto_renewal_notice_trap",
    "no_termination_for_convenience_customer",
    "early_termination_fee",
    "minimum_commitment_lock_in",
    "auto_renewal_hidden_cancellation_burden",
}

_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS = {
    "payment_deadline_pressure",
    "service_suspension_right",
    "fee_acceleration_late_fee_exposure",
    "payment_withholding_dispute_charge_leverage",
    "cross_payment_leverage_stack",
}

_PAYMENT_SUPPORT_RULE_IDS = {
    "payment_deadline_pressure",
    "fee_acceleration_late_fee_exposure",
    "payment_collection_cost_shifting",
    "payment_withholding_dispute_charge_leverage",
    "cross_payment_leverage_stack",
}

_EXIT_PRESSURE_SIGNAL_RULE_IDS = {
    "auto_renewal_silent",
    "renewal_notice_window_pressure",
    "renewal_long_commitment",
    "auto_renewal_notice_trap",
    "termination_without_notice",
    "termination_assistance_exit_dependency",
    "no_termination_for_convenience_customer",
    "early_termination_fee",
    "minimum_commitment_lock_in",
    "auto_renewal_hidden_cancellation_burden",
}

_CONTROL_RIGHT_RULE_IDS = {
    "unilateral_amendment_policy_reference",
    "unilateral_price_increase",
    "service_suspension_right",
    "termination_for_convenience_counterparty",
    "broad_customer_data_use",
    "assignment_without_consent",
    "change_of_control_assignment",
    "broad_sublicensing_right",
    "subcontracting_without_consent",
    "unilateral_change_control_scope_terms",
    "weak_sla_service_remedy_suspension",
    "data_retention_deletion_asymmetry",
    "data_transfer_anonymisation_processing",
}

_RENEWAL_EXIT_TRAP_RULE_IDS = {
    "auto_renewal_silent",
    "renewal_notice_window_pressure",
    "renewal_long_commitment",
    "auto_renewal_notice_trap",
    "auto_renewal_hidden_cancellation_burden",
}

_RENEWAL_ECONOMIC_CHANGE_RULE_IDS = {
    "renewal_price_increase_on_renewal",
    "unilateral_price_increase",
    "unilateral_amendment_policy_reference",
}

_HARD_EXIT_LOCKIN_RULE_IDS = {
    "no_termination_for_convenience_customer",
    "early_termination_fee",
    "minimum_commitment_lock_in",
    "termination_assistance_exit_dependency",
}

_EXIT_COST_RULE_IDS = {
    "early_termination_fee",
    "minimum_commitment_lock_in",
    "fee_acceleration_late_fee_exposure",
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


_TOP_RISK_STRUCTURAL_RULE_IDS = {
    "cross_exit_trap_stack",
    "cross_auto_renewal_notice_exit_trap",
    "cross_renewal_price_exit_trap",
    "cross_termination_fee_lock_in",
    "cross_supplier_control_customer_lock_in",
    "cross_control_without_reciprocal_exit",
    "cross_payment_leverage_stack",
    "cross_payment_exit_pressure",
    "cross_suspension_payment_control",
    "cross_variation_payment_leverage",
    "cross_unilateral_variation_limited_exit",
    "cross_renewal_price_lock_in",
    "sector_saas_subscription_lock_in",
    "sector_saas_operational_dependency",
    "sector_supplier_control_stack",
    "sector_data_secondary_use_risk",
    "sector_data_exit_residue_risk",
    "cross_audit_data_confidentiality_exposure",
    "cross_change_control_weak_remedies",
    "cross_ip_asset_leakage",
    "cross_force_majeure_continuity_lock_in",
    "cross_low_cap_broad_indemnity",
    "cross_termination_no_refund",
    "cross_data_confidentiality_gap",
    "cross_upfront_payment_suspension",
    "cross_public_sector_supplier_burden",
    "cross_supplier_performance_financial_exposure",
    "cross_data_public_authority_disclosure_stack",
}

_TOP_RISK_MATERIAL_DATA_RULE_IDS = {
    "sector_data_secondary_use_risk",
    "sector_data_exit_residue_risk",
    "broad_customer_data_use",
    "data_retention_deletion_asymmetry",
    "data_transfer_anonymisation_processing",
}

_TOP_RISK_THIN_SIGNAL_RULE_IDS = {
    "broad_sublicensing_right",
}

_TOP_RISK_CATEGORY_PRIORITY = {
    "termination": 5,
    "payment": 4,
    "data": 4,
    "jurisdiction": 4,
    "liability": 3,
    "indemnity": 3,
    "service": 3,
    "control": 3,
    "amendment": 3,
    "licensing": 1,
    "ip": 4,
    "force_majeure": 3,
    "delivery": 4,
    "remedy": 4,
    "insurance": 2,
    "governance": 1,
    "audit": 3,
    "survival": 3,
    "restraint": 3,
}


_SAAS_TEXT_SIGNAL_PATTERNS: List[Tuple[str, str]] = [
    ("subscription", r"\bsubscription\b"),
    ("saas", r"\bsaas\b"),
    ("platform", r"\bplatform\b"),
    ("hosted service", r"\bhosted\s+service\b"),
    ("software", r"\bsoftware\b"),
    ("api", r"\bapi\b"),
    ("user accounts", r"\buser\s+accounts?\b"),
    ("accounts", r"\baccounts?\b"),
    ("dashboard", r"\bdashboard\b"),
    ("uptime", r"\buptime\b"),
    ("availability", r"\bavailability\b"),
    ("service credits", r"\bservice\s+credits?\b"),
]

_SUPPLIER_TEXT_SIGNAL_PATTERNS: List[Tuple[str, str]] = [
    ("supplier", r"\bsupplier\b"),
    ("statement of work", r"\bstatement\s+of\s+work\b|\bsow\b"),
    ("purchase order", r"\bpurchase\s+order\b|\bpo\b"),
    ("deliverables", r"\bdeliverables?\b"),
    ("service levels", r"\bservice\s+levels?\b"),
    ("milestones", r"\bmilestones?\b"),
    ("subcontractors", r"\bsubcontractors?\b"),
    ("scope of work", r"\bscope\s+of\s+work\b"),
]

_DATA_TEXT_SIGNAL_PATTERNS: List[Tuple[str, str]] = [
    ("customer data", r"\bcustomer\s+data\b"),
    ("personal data", r"\bpersonal\s+data\b"),
    ("usage data", r"\busage\s+data\b"),
    ("aggregated data", r"\baggregated\s+data\b"),
    ("analytics", r"\banalytics\b"),
    ("retention", r"\bretention\b"),
    ("deletion", r"\bdeletion\b|\bdelete\b"),
    ("subprocessors", r"\bsubprocessors?\b"),
    ("data processing", r"\bdata\s+processing\b"),
    ("data export", r"\bdata\s+export\b"),
    ("cross-border transfer", r"\bcross-?border\b|\bonward\s+transfer\b"),
    ("anonymised data", r"\banonymi[sz]ed\s+data\b|\bde-?identified\s+data\b"),
]

_PLAYBOOK_RULE_HINTS: Dict[str, set[str]] = {
    "saas_contract": {
        "auto_renewal_silent",
        "renewal_notice_window_pressure",
        "renewal_long_commitment",
        "auto_renewal_notice_trap",
        "renewal_price_increase_on_renewal",
        "service_suspension_right",
        "payment_deadline_pressure",
        "fee_acceleration_late_fee_exposure",
        "termination_assistance_exit_dependency",
        "service_credits_sole_remedy",
        "broad_warranty_disclaimer",
        "data_retention_deletion_asymmetry",
    },
    "supplier_service_contract": {
        "unilateral_amendment_policy_reference",
        "unilateral_price_increase",
        "subcontracting_without_consent",
        "assignment_without_consent",
        "change_of_control_assignment",
        "termination_assistance_exit_dependency",
        "service_suspension_right",
        "termination_for_convenience_counterparty",
    },
    "data_heavy_contract": {
        "broad_customer_data_use",
        "broad_sublicensing_right",
        "data_retention_deletion_asymmetry",
        "data_security_responsibility_imbalance",
        "data_transfer_anonymisation_processing",
        "confidentiality_survival_gap_or_imbalance",
        "termination_assistance_exit_dependency",
    },
}

_PLAYBOOK_FOCUS_AREAS: Dict[str, List[str]] = {
    "saas_contract": ["subscription lock-in", "service continuity", "data transition"],
    "supplier_service_contract": ["delivery control", "subcontracting and assignment", "exit leverage"],
    "data_heavy_contract": ["secondary data use", "retention and deletion", "post-termination data handling"],
}

_SECTOR_DATA_RIGHT_RULE_IDS = {
    "broad_customer_data_use",
    "broad_sublicensing_right",
    "data_retention_deletion_asymmetry",
}

_SECTOR_DATA_EXIT_RULE_IDS = {
    "termination_assistance_exit_dependency",
    "no_termination_for_convenience_customer",
    "early_termination_fee",
    "minimum_commitment_lock_in",
    "auto_renewal_notice_trap",
    "renewal_long_commitment",
}

_AUDIT_GOVERNANCE_RULE_IDS = {
    "intrusive_audit_rights",
    "audit_access_cost_confidentiality",
}

_CONFIDENTIALITY_WEAKNESS_RULE_IDS = {
    "confidentiality_survival_gap_or_imbalance",
    "survival_clause_risk_concentration",
}

_DATA_GOVERNANCE_RULE_IDS = {
    "broad_customer_data_use",
    "data_transfer_anonymisation_processing",
    "data_retention_deletion_asymmetry",
    "data_security_responsibility_imbalance",
}

_CHANGE_CONTROL_RULE_IDS = {
    "unilateral_amendment_policy_reference",
    "unilateral_change_control_scope_terms",
    "unilateral_price_increase",
}

_WEAK_SERVICE_REMEDY_RULE_IDS = {
    "service_credits_sole_remedy",
    "exclusive_remedy_limitation",
    "weak_sla_service_remedy_suspension",
    "service_suspension_right",
}

_IP_ASSET_CONTROL_RULE_IDS = {
    "ip_ownership_foreground_conflict",
    "ip_broad_license_or_residuals",
    "broad_sublicensing_right",
}

_FORCE_MAJEURE_WEAK_EXIT_RULE_IDS = {
    "no_termination_for_convenience_customer",
    "termination_assistance_exit_dependency",
    "auto_renewal_notice_trap",
    "renewal_long_commitment",
}


_CONTROLLED_SYNTHESIS_SCORE_CAP = 4

_LOW_LIABILITY_CAP_RULE_IDS = {
    "liability_cap_present",
}

_CONTROLLED_INDEMNITY_RULE_IDS = {
    "indemnity_broad",
    "indemnity_one_way",
    "liability_super_cap_carveout",
    "supplier_broad_indemnity_public_sector",
}

_TERMINATION_CONVENIENCE_RULE_IDS = {
    "termination_for_convenience_counterparty",
    "unilateral_termination_for_convenience",
}

_NO_REFUND_RULE_IDS = {
    "non_refundable_fees",
}

_CONTROLLED_DATA_RIGHT_RULE_IDS = {
    "broad_customer_data_use",
    "broad_sublicensing_right",
    "data_transfer_anonymisation_processing",
}

_CONTROLLED_CONFIDENTIALITY_WEAKNESS_RULE_IDS = {
    "confidentiality_survival_gap_or_imbalance",
    "survival_clause_risk_concentration",
}

_UPFRONT_PAYMENT_RULE_IDS = {
    "non_refundable_fees",
}

_SUPPLIER_SUSPENSION_RULE_IDS = {
    "service_suspension_right",
    "weak_sla_service_remedy_suspension",
}

_PUBLIC_SECTOR_SUPPLIER_BURDEN_RULE_IDS = {
    "supplier_broad_indemnity_public_sector",
    "broad_buyer_termination",
    "delivery_failure_cancellation",
    "time_is_of_essence_delivery",
    "cross_contract_set_off",
    "step_in_cover_cost_recovery",
    "enhanced_liquidated_damages",
    "liquidated_damages_financial_exposure",
    "delay_discount_or_service_credit",
    "confidentiality_foia_public_disclosure",
    "public_procurement_variation_constraint",
}

_SUPPLIER_PERFORMANCE_FINANCIAL_EXPOSURE_RULE_IDS = {
    "liquidated_damages_financial_exposure",
    "enhanced_liquidated_damages",
    "delay_discount_or_service_credit",
    "cross_contract_set_off",
    "post_termination_completion_cost_recovery",
    "supplier_broad_indemnity_public_sector",
    "time_is_of_essence_delivery",
    "step_in_cover_cost_recovery",
}

_DATA_PUBLIC_AUTHORITY_DISCLOSURE_RULE_IDS = {
    "outdated_data_protection_framework",
    "data_transfer_anonymisation_processing",
    "confidentiality_foia_public_disclosure",
    "audit_access_cost_confidentiality",
    "intrusive_audit_rights",
}

_LOW_LIABILITY_CAP_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("low cap tied to fees paid", r"\bliabilit(?:y|ies)\b.{0,160}\b(?:limited\s+to|shall\s+not\s+exceed|capped\s+at)\b.{0,120}\b(?:fees?|amounts?|charges?)\s+paid\b.{0,80}\b(?:12|twelve|6|six|3|three)\s+months?\b"),
    ("low cap tied to one month fees", r"\bliabilit(?:y|ies)\b.{0,160}\b(?:limited\s+to|shall\s+not\s+exceed|capped\s+at)\b.{0,100}\b(?:one|1)\s+month'?s?\s+fees?\b"),
    ("low liability cap", r"\blow\s+liabilit(?:y|ies)\s+cap\b|\blow\s+cap\s+on\s+liabilit(?:y|ies)\b"),
]

_INDEMNITY_ESCALATION_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("uncapped indemnity", r"\bindemni(?:ty|ties|fication|fy|fies)\b.{0,160}\b(?:uncapped|without\s+limit|not\s+subject\s+to\s+(?:the\s+)?(?:liability\s+)?cap)\b"),
    ("indemnity carve-out", r"\b(?:liability\s+)?cap\b.{0,160}\b(?:shall\s+not\s+apply|does\s+not\s+apply|excludes?|carve-?out)\b.{0,120}\bindemni(?:ty|ties|fication|fy|fies)\b"),
    ("third-party indemnity", r"\bindemni(?:fy|fies|fication|ty|ties)\b.{0,140}\bthird-?party\s+claims?\b"),
]

_NO_REFUND_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("no refunds", r"\bno\s+refunds?\b"),
    ("non-refundable prepaid fees", r"\bprepaid\s+fees?\b.{0,100}\bnon-?refundable\b|\bnon-?refundable\b.{0,100}\bprepaid\s+fees?\b"),
    ("retained prepaid sums", r"\b(?:retain|keeps?|keep)\b.{0,120}\bprepaid\s+(?:fees?|sums?|amounts?)\b"),
]

_DATA_RIGHT_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("AI training use", r"\b(?:customer|client|personal|usage)?\s*data\b.{0,180}\b(?:train|training|artificial\s+intelligence|machine\s+learning|\bai\b)\b"),
    ("onward transfer", r"\bonward\s+transfer\b|\bmay\s+(?:transfer|disclose)\b.{0,140}\b(?:customer|client|personal)\s+data\b"),
    ("sublicensing data", r"\b(?:sublicen[cs]e|sub-license)\b.{0,120}\b(?:customer|client|personal|usage)?\s*data\b"),
    ("broad disclosure", r"\bdisclose\b.{0,140}\b(?:customer|client|personal)\s+data\b.{0,120}\b(?:affiliates|third\s+parties|partners)\b"),
]

_WEAK_CONFIDENTIALITY_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("missing confidentiality", r"\bno\s+confidentiality\s+obligations?\b|\bwithout\s+confidentiality\s+obligations?\b"),
    ("short confidentiality survival", r"\bconfidential(?:ity|\s+information)\b.{0,160}\bsurviv(?:e|al)\b.{0,100}\b(?:6|six|12|twelve)\s+months?\b"),
    ("broad confidentiality exception", r"\bconfidential(?:ity|\s+information)\b.{0,180}\b(?:residual\s+knowledge|independently\s+remembered|general\s+knowledge)\b"),
]

_UPFRONT_PAYMENT_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("upfront payment", r"\b(?:upfront|up-front|advance)\s+payment\b|\bpayment\s+in\s+advance\b"),
    ("prepaid fees", r"\bprepaid\s+fees?\b"),
    ("front-loaded milestone", r"\bfront-?loaded\s+milestone\s+payments?\b|\bmilestone\s+payments?\b.{0,100}\bbefore\s+delivery\b"),
    ("payment before delivery", r"\bpayment\b.{0,100}\bbefore\s+(?:delivery|acceptance|go-?live)\b"),
]

_BROAD_SUSPENSION_TEXT_PATTERNS: List[Tuple[str, str]] = [
    ("disputed sums suspension", r"\bsuspend\b.{0,160}\bdisputed\s+(?:sums?|amounts?|invoices?)\b|\bdisputed\s+(?:sums?|amounts?|invoices?)\b.{0,160}\bsuspend\b"),
    ("immediate suspension", r"\bsuspend\b.{0,140}\b(?:immediately|without\s+(?:notice|cure))\b"),
    ("minor payment suspension", r"\bsuspend\b.{0,160}\b(?:minor|unresolved)\s+payment\s+(?:issue|dispute)\b"),
]


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
    matched_pattern: str = "derived_cross_clause",
    tags: Optional[List[str]] = None,
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
        "matched_pattern": matched_pattern,
        "match_span": span,
        "matched_text": _combine_excerpt(contributors, limit=1),
        "matched_location": None,
        "context_note": None,
        "excerpt": _combine_excerpt(contributors),
        "tags": tags or ["cross_clause", "derived_signal"],
        "triggered_by": triggered_by,
    }



def _collect_text_signals(text: str, signal_patterns: List[Tuple[str, str]]) -> List[str]:
    matched: List[str] = []
    for label, pattern in signal_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            matched.append(label)
    return matched


def _collect_rule_signals(rule_ids: set[str], candidates: set[str]) -> List[str]:
    return [
        LABEL_ALIASES.get(rule_id, rule_id).replace("-", " ")
        for rule_id in sorted(rule_ids.intersection(candidates))
    ]


def _infer_sector_playbooks(text: str, matched_rule_ids: set[str]) -> List[Dict[str, Any]]:
    playbooks: List[Dict[str, Any]] = []
    lowered = text.lower()

    saas_text = _collect_text_signals(lowered, _SAAS_TEXT_SIGNAL_PATTERNS)
    saas_rule_signals = _collect_rule_signals(matched_rule_ids, _PLAYBOOK_RULE_HINTS["saas_contract"])
    if len(saas_text) >= 3 or (len(saas_text) >= 2 and len(saas_rule_signals) >= 2):
        matched_signals = list(dict.fromkeys(saas_text + saas_rule_signals))[:6]
        playbooks.append(
            {
                "id": "saas_contract",
                "signal_count": len(matched_signals),
                "matched_signals": matched_signals,
                "focus_areas": _PLAYBOOK_FOCUS_AREAS["saas_contract"],
            }
        )

    supplier_text = _collect_text_signals(lowered, _SUPPLIER_TEXT_SIGNAL_PATTERNS)
    supplier_rule_signals = _collect_rule_signals(matched_rule_ids, _PLAYBOOK_RULE_HINTS["supplier_service_contract"])
    if len(supplier_text) >= 3 or (len(supplier_text) >= 2 and len(supplier_rule_signals) >= 2):
        matched_signals = list(dict.fromkeys(supplier_text + supplier_rule_signals))[:6]
        playbooks.append(
            {
                "id": "supplier_service_contract",
                "signal_count": len(matched_signals),
                "matched_signals": matched_signals,
                "focus_areas": _PLAYBOOK_FOCUS_AREAS["supplier_service_contract"],
            }
        )

    data_text = _collect_text_signals(lowered, _DATA_TEXT_SIGNAL_PATTERNS)
    data_rule_signals = _collect_rule_signals(matched_rule_ids, _PLAYBOOK_RULE_HINTS["data_heavy_contract"])
    if len(data_text) >= 2 or (len(data_text) >= 1 and len(data_rule_signals) >= 2):
        matched_signals = list(dict.fromkeys(data_text + data_rule_signals))[:6]
        playbooks.append(
            {
                "id": "data_heavy_contract",
                "signal_count": len(matched_signals),
                "matched_signals": matched_signals,
                "focus_areas": _PLAYBOOK_FOCUS_AREAS["data_heavy_contract"],
            }
        )

    return playbooks


def _build_sector_synthesis_findings(
    text: str,
    findings: List[Dict[str, Any]],
    matched_rule_ids: set[str],
    sector_playbooks: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not sector_playbooks:
        return [], []

    playbook_ids = {str(playbook.get("id", "")) for playbook in sector_playbooks}
    by_rule_id: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        by_rule_id.setdefault(str(finding.get("rule_id", "")), []).append(finding)

    sector_findings: List[Dict[str, Any]] = []
    sector_adjustments: List[Dict[str, Any]] = []
    lowered = text.lower()

    if "saas_contract" in playbook_ids:
        matched_renewal = sorted(matched_rule_ids.intersection(_RENEWAL_EXIT_TRAP_RULE_IDS))
        matched_pricing = sorted(matched_rule_ids.intersection(_RENEWAL_ECONOMIC_CHANGE_RULE_IDS))
        matched_payment = sorted(matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS))
        matched_exit = sorted(matched_rule_ids.intersection(_HARD_EXIT_LOCKIN_RULE_IDS.union({"termination_without_notice"})))
        if matched_renewal and matched_exit and (matched_pricing or matched_payment):
            triggered_by = list(dict.fromkeys(matched_renewal + matched_pricing + matched_payment + matched_exit))
            contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
            overlapping_major = {"cross_exit_trap_stack", "cross_renewal_price_exit_trap"}.intersection(matched_rule_ids)
            stronger = bool(matched_pricing and matched_payment) or len(matched_exit) >= 2
            effect = 1 if overlapping_major else (2 if stronger else 1)
            sector_findings.append(
                _derived_finding(
                    rule_id="sector_saas_subscription_lock_in",
                    category="renewal",
                    title="SaaS subscription lock-in",
                    severity=4 if stronger else 3,
                    weight=max(effect, 1),
                    rationale="Subscription-style SaaS signals appear alongside renewal pressure, changing economics, and constrained exit, which can create recurring-cost lock-in and operational dependency.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                    matched_pattern="derived_sector_playbook",
                    tags=["sector_playbook", "derived_signal", "saas_contract"],
                )
            )
            sector_adjustments.append(
                {
                    "type": "sector_synthesis",
                    "rule_id": "sector_saas_subscription_lock_in",
                    "effect": effect,
                    "reason": "In a subscription SaaS context, renewal pressure combined with pricing change or payment leverage can make recurring-cost lock-in more commercially significant.",
                    "triggered_by": triggered_by,
                }
            )

        saas_dependency_support = sorted(
            matched_rule_ids.intersection(
                {
                    "cross_payment_leverage_stack",
                    "cross_suspension_payment_control",
                    "payment_deadline_pressure",
                    "fee_acceleration_late_fee_exposure",
                    "termination_assistance_exit_dependency",
                    "data_retention_deletion_asymmetry",
                    "service_credits_sole_remedy",
                    "broad_warranty_disclaimer",
                }
            )
        )
        if "service_suspension_right" in matched_rule_ids and saas_dependency_support:
            triggered_by = list(dict.fromkeys(["service_suspension_right"] + saas_dependency_support))
            contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
            stronger = len([rid for rid in saas_dependency_support if rid != "cross_suspension_payment_control"]) >= 2
            effect = 1 if "cross_suspension_payment_control" in matched_rule_ids else (2 if stronger else 1)
            sector_findings.append(
                _derived_finding(
                    rule_id="sector_saas_operational_dependency",
                    category="payment",
                    title="SaaS operational dependency exposure",
                    severity=4 if stronger else 3,
                    weight=max(effect, 1),
                    rationale="SaaS service access appears tied to suspension, continuity, or exit-transition pressure, which can turn operational dependency into commercial leverage.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                    matched_pattern="derived_sector_playbook",
                    tags=["sector_playbook", "derived_signal", "saas_contract"],
                )
            )
            sector_adjustments.append(
                {
                    "type": "sector_synthesis",
                    "rule_id": "sector_saas_operational_dependency",
                    "effect": effect,
                    "reason": "In SaaS contracts, suspension rights combined with weak continuity or transition support can make service access itself a leverage point.",
                    "triggered_by": triggered_by,
                }
            )

    if "supplier_service_contract" in playbook_ids:
        matched_supplier_control = sorted(matched_rule_ids.intersection(_CONTROL_RIGHT_RULE_IDS.union(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS)))
        matched_supplier_exit = sorted(matched_rule_ids.intersection(_LIMITED_EXIT_RULE_IDS.union({"termination_without_notice"})))
        non_variation_controls = [rid for rid in matched_supplier_control if rid not in _VARIATION_RULE_IDS]
        if len(matched_supplier_control) >= 2 and matched_supplier_exit and non_variation_controls:
            triggered_by = list(dict.fromkeys(matched_supplier_control + matched_supplier_exit))
            contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
            stronger = len(matched_supplier_control) >= 3 or "service_suspension_right" in matched_supplier_control
            overlapping_major = {"cross_control_without_reciprocal_exit", "cross_supplier_control_customer_lock_in"}.intersection(matched_rule_ids)
            effect = 1 if overlapping_major else (2 if stronger else 1)
            sector_findings.append(
                _derived_finding(
                    rule_id="sector_supplier_control_stack",
                    category="termination",
                    title="Supplier control stack in service delivery",
                    severity=4 if stronger else 3,
                    weight=max(effect, 1),
                    rationale="Service-delivery signals appear alongside supplier control rights and constrained customer exit, which can let the counterparty shift delivery structure or commercial control while the customer remains exposed.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                    matched_pattern="derived_sector_playbook",
                    tags=["sector_playbook", "derived_signal", "supplier_service_contract"],
                )
            )
            sector_adjustments.append(
                {
                    "type": "sector_synthesis",
                    "rule_id": "sector_supplier_control_stack",
                    "effect": effect,
                    "reason": "In supplier-service contracts, control rights combined with weak customer exit can make delivery or governance changes more commercially dangerous.",
                    "triggered_by": triggered_by,
                }
            )

    if "data_heavy_contract" in playbook_ids:
        matched_data_rights = sorted(matched_rule_ids.intersection(_SECTOR_DATA_RIGHT_RULE_IDS.union({"broad_customer_data_use", "broad_sublicensing_right"})))
        analytics_support = bool(re.search(r"\b(?:aggregated\s+data|analytics|usage\s+data)\b", lowered))
        if matched_data_rights and (len(matched_data_rights) >= 2 or analytics_support):
            triggered_by = list(dict.fromkeys(matched_data_rights))
            contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
            stronger = len(matched_data_rights) >= 3 or (len(matched_data_rights) >= 2 and analytics_support)
            effect = 2 if stronger else 1
            sector_findings.append(
                _derived_finding(
                    rule_id="sector_data_secondary_use_risk",
                    category="data",
                    title="Sector data secondary-use risk",
                    severity=4 if stronger else 3,
                    weight=effect,
                    rationale="Data-heavy contract signals appear alongside broad use, sublicensing, analytics, or retention rights, which may allow customer data to be used or retained beyond the intended operational purpose.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                    matched_pattern="derived_sector_playbook",
                    tags=["sector_playbook", "derived_signal", "data_heavy_contract"],
                )
            )
            sector_adjustments.append(
                {
                    "type": "sector_synthesis",
                    "rule_id": "sector_data_secondary_use_risk",
                    "effect": effect,
                    "reason": "In data-heavy agreements, broad use and retention rights can carry more significance because the contract appears to govern ongoing data processing and analytics activity.",
                    "triggered_by": triggered_by,
                }
            )

        matched_data_exit = sorted(matched_rule_ids.intersection(_SECTOR_DATA_EXIT_RULE_IDS))
        if "data_retention_deletion_asymmetry" in matched_rule_ids and matched_data_exit and matched_data_rights:
            triggered_by = list(dict.fromkeys(["data_retention_deletion_asymmetry"] + matched_data_exit + matched_data_rights))
            contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
            stronger = (
                "termination_assistance_exit_dependency" in matched_data_exit
                and any(rid in {"broad_customer_data_use", "broad_sublicensing_right"} for rid in matched_data_rights)
            )
            effect = 2 if stronger else 1
            sector_findings.append(
                _derived_finding(
                    rule_id="sector_data_exit_residue_risk",
                    category="data",
                    title="Data residue risk after exit",
                    severity=4 if stronger else 3,
                    weight=effect,
                    rationale="Data-heavy contract signals appear alongside retention asymmetry and exit-related weaknesses, which may leave customer data exposed beyond the end of the intended commercial relationship.",
                    triggered_by=triggered_by,
                    contributors=contributors,
                    matched_pattern="derived_sector_playbook",
                    tags=["sector_playbook", "derived_signal", "data_heavy_contract"],
                )
            )
            sector_adjustments.append(
                {
                    "type": "sector_synthesis",
                    "rule_id": "sector_data_exit_residue_risk",
                    "effect": effect,
                    "reason": "In data-heavy agreements, weak deletion or transition support can leave data exposure in place after the contract should have been commercially concluded.",
                    "triggered_by": triggered_by,
                }
            )

    return sector_findings, sector_adjustments


def _apply_risk_appetite(
    adjusted_score: int,
    findings: List[Dict[str, Any]],
    risk_appetite: str,
) -> Tuple[int, str, List[Dict[str, Any]]]:
    selected = (risk_appetite or "balanced").strip().lower()
    if selected not in {"balanced", "strict", "conservative"}:
        selected = "balanced"

    if selected == "balanced":
        return adjusted_score, selected, []

    derived_rule_ids = {
        str(f.get("rule_id", ""))
        for f in findings
        if str(f.get("matched_pattern", "")).startswith("derived_")
    }
    high_severity_count = sum(1 for f in findings if int(f.get("severity", 0)) >= 4)
    effect = 0
    reason = ""

    if selected == "strict":
        if derived_rule_ids and adjusted_score >= 4:
            effect = 1
            reason = "Strict appetite keeps combined medium-risk structures review-elevating instead of allowing them to read as routine."
        elif high_severity_count >= 3 and adjusted_score >= 4:
            effect = 1
            reason = "Strict appetite treats multiple material signals as a stronger review case even when each clause is individually bounded."

    if selected == "conservative":
        if len(derived_rule_ids) >= 2:
            effect = 1
            reason = "Conservative appetite adds a bounded caution uplift when several derived risk structures appear together."
        elif derived_rule_ids and high_severity_count >= 2:
            effect = 1
            reason = "Conservative appetite keeps materially combined risks from reading as comfortably routine."

    if effect <= 0:
        return adjusted_score, selected, []

    return (
        adjusted_score + effect,
        selected,
        [
            {
                "type": "risk_appetite",
                "rule_id": f"risk_appetite_{selected}",
                "effect": effect,
                "reason": reason,
                "triggered_by": sorted(derived_rule_ids)[:6],
            }
        ],
    )



def _text_signal_labels(text: str, signal_patterns: List[Tuple[str, str]]) -> List[str]:
    return [
        label
        for label, pattern in signal_patterns
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]


def _first_contributors(
    by_rule_id: Dict[str, List[Dict[str, Any]]],
    rule_ids: List[str],
) -> List[Dict[str, Any]]:
    contributors: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for rule_id in rule_ids:
        if rule_id in seen or rule_id not in by_rule_id:
            continue
        contributors.append(by_rule_id[rule_id][0])
        seen.add(rule_id)
    return contributors


def _controlled_synthesis_finding(
    *,
    rule_id: str,
    category: str,
    title: str,
    severity: int,
    rationale: str,
    why_it_matters: str,
    triggered_by: List[str],
    contributors: List[Dict[str, Any]],
    pattern: str,
    confidence: float = 0.82,
) -> Dict[str, Any]:
    finding = _derived_finding(
        rule_id=rule_id,
        category=category,
        title=title,
        severity=severity,
        weight=1,
        rationale=rationale,
        triggered_by=triggered_by,
        contributors=contributors,
        matched_pattern=f"derived_cross_clause_{pattern}",
        tags=["cross_clause", "derived_signal", pattern],
    )
    finding.update(
        {
            "why_it_matters": why_it_matters,
            "confidence": confidence,
            "pattern": pattern,
            "synthesis_pattern": pattern,
            "linked_rule_ids": triggered_by,
            "linked_base_rule_ids": triggered_by,
            "audit": SYNTHESIS_PATTERN_METADATA.get(pattern, {}),
        }
    )
    return finding


def _add_controlled_cross_clause_pattern(
    *,
    cross_findings: List[Dict[str, Any]],
    cross_adjustments: List[Dict[str, Any]],
    existing_rule_ids: set[str],
    pattern: str,
    rule_id: str,
    category: str,
    title: str,
    severity: int,
    rationale: str,
    why_it_matters: str,
    triggered_by: List[str],
    contributors: List[Dict[str, Any]],
    reason: str,
    remaining_score_room: int,
) -> int:
    if rule_id in existing_rule_ids or remaining_score_room <= 0 or not contributors:
        return 0

    triggered = list(dict.fromkeys(triggered_by))
    cross_findings.append(
        _controlled_synthesis_finding(
            rule_id=rule_id,
            category=category,
            title=title,
            severity=severity,
            rationale=rationale,
            why_it_matters=why_it_matters,
            triggered_by=triggered,
            contributors=contributors,
            pattern=pattern,
        )
    )
    cross_adjustments.append(
        {
            "type": "cross_clause",
            "pattern": pattern,
            "rule_id": rule_id,
            "effect": 1,
            "impact": 1,
            "reason": reason,
            "triggered_by": triggered,
            "audit": SYNTHESIS_PATTERN_METADATA.get(pattern, {}),
        }
    )
    existing_rule_ids.add(rule_id)
    return 1


def _build_controlled_cross_clause_findings(
    text: str,
    findings: List[Dict[str, Any]],
    matched_rule_ids: set[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    by_rule_id: Dict[str, List[Dict[str, Any]]] = {}
    for finding in findings:
        by_rule_id.setdefault(str(finding.get("rule_id", "")), []).append(finding)

    cross_findings: List[Dict[str, Any]] = []
    cross_adjustments: List[Dict[str, Any]] = []
    existing_rule_ids = set(matched_rule_ids)
    remaining_score_room = _CONTROLLED_SYNTHESIS_SCORE_CAP

    low_cap_text = _text_signal_labels(text, _LOW_LIABILITY_CAP_TEXT_PATTERNS)
    indemnity_text = _text_signal_labels(text, _INDEMNITY_ESCALATION_TEXT_PATTERNS)
    matched_low_cap = sorted(matched_rule_ids.intersection(_LOW_LIABILITY_CAP_RULE_IDS))
    matched_indemnity = sorted(matched_rule_ids.intersection(_CONTROLLED_INDEMNITY_RULE_IDS))
    has_low_cap = bool(matched_low_cap and low_cap_text)
    has_indemnity = bool(matched_indemnity or indemnity_text)
    if has_low_cap and has_indemnity:
        triggered_by = matched_low_cap + matched_indemnity + low_cap_text + indemnity_text
        contributors = _first_contributors(by_rule_id, matched_low_cap + matched_indemnity)
        stronger = "liability_super_cap_carveout" in matched_indemnity or any(
            signal in {"uncapped indemnity", "indemnity carve-out"} for signal in indemnity_text
        )
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="low_cap_broad_indemnity",
            rule_id="cross_low_cap_broad_indemnity",
            category="liability",
            title="Liability cap may be weakened by indemnity obligations outside the cap",
            severity=5 if stronger else 4,
            rationale="A low general liability cap may appear protective, but broad indemnity obligations or carve-outs may reduce the practical protection of the cap.",
            why_it_matters="Hidden exposure: cap protection may be weaker than it appears.",
            triggered_by=triggered_by,
            contributors=contributors,
            reason="Low cap language and broad indemnity or carve-out signals combine into weaker practical cap protection.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    no_refund_text = _text_signal_labels(text, _NO_REFUND_TEXT_PATTERNS)
    matched_termination = sorted(matched_rule_ids.intersection(_TERMINATION_CONVENIENCE_RULE_IDS))
    matched_no_refund = sorted(matched_rule_ids.intersection(_NO_REFUND_RULE_IDS))
    if matched_termination and (matched_no_refund or no_refund_text):
        triggered_by = matched_termination + matched_no_refund + no_refund_text
        contributors = _first_contributors(by_rule_id, matched_termination + matched_no_refund)
        stronger = "non-refundable prepaid fees" in no_refund_text or "retained prepaid sums" in no_refund_text
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="termination_no_refund",
            rule_id="cross_termination_no_refund",
            category="termination",
            title="Termination rights combined with lack of refund may create asymmetric exposure",
            severity=5 if stronger else 4,
            rationale="One party may be able to exit while retaining prepaid sums or denying refund rights, creating commercial imbalance.",
            why_it_matters="Asymmetric exposure: exit rights may leave prepaid economics with the terminating or non-performing side.",
            triggered_by=triggered_by,
            contributors=contributors,
            reason="Termination-for-convenience signals combine with non-refundable or retained prepaid-fee language.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    data_text = _text_signal_labels(text, _DATA_RIGHT_TEXT_PATTERNS)
    weak_conf_text = _text_signal_labels(text, _WEAK_CONFIDENTIALITY_TEXT_PATTERNS)
    matched_data_rights = sorted(matched_rule_ids.intersection(_CONTROLLED_DATA_RIGHT_RULE_IDS))
    matched_weak_conf = sorted(matched_rule_ids.intersection(_CONTROLLED_CONFIDENTIALITY_WEAKNESS_RULE_IDS))
    if (matched_data_rights or data_text) and (matched_weak_conf or weak_conf_text):
        triggered_by = matched_data_rights + matched_weak_conf + data_text + weak_conf_text
        contributors = _first_contributors(by_rule_id, matched_data_rights + matched_weak_conf)
        stronger = bool(
            matched_data_rights.intersection({"broad_customer_data_use", "broad_sublicensing_right", "data_transfer_anonymisation_processing"})
            if isinstance(matched_data_rights, set)
            else any(rid in {"broad_customer_data_use", "broad_sublicensing_right", "data_transfer_anonymisation_processing"} for rid in matched_data_rights)
        ) or any(signal in {"AI training use", "onward transfer", "sublicensing data"} for signal in data_text)
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="data_confidentiality_gap",
            rule_id="cross_data_confidentiality_gap",
            category="data",
            title="Broad data rights combined with weak confidentiality may increase governance risk",
            severity=5 if stronger else 4,
            rationale="Broad rights to use, disclose, transfer, sublicense, analyse, or train on data become materially riskier where confidentiality limits or survival protections are weak.",
            why_it_matters="Governance risk: expanded data rights may outlast or outrun confidentiality controls.",
            triggered_by=triggered_by,
            contributors=contributors,
            reason="Broad data-use or transfer signals combine with weak confidentiality or survival controls.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    upfront_text = _text_signal_labels(text, _UPFRONT_PAYMENT_TEXT_PATTERNS)
    suspension_text = _text_signal_labels(text, _BROAD_SUSPENSION_TEXT_PATTERNS)
    matched_upfront = sorted(matched_rule_ids.intersection(_UPFRONT_PAYMENT_RULE_IDS)) if upfront_text else []
    matched_suspension = sorted(matched_rule_ids.intersection(_SUPPLIER_SUSPENSION_RULE_IDS))

    matched_public_burden = sorted(matched_rule_ids.intersection(_PUBLIC_SECTOR_SUPPLIER_BURDEN_RULE_IDS))
    if len(matched_public_burden) >= 3:
        contributors = _first_contributors(by_rule_id, matched_public_burden)
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="cross_public_sector_supplier_burden",
            rule_id="cross_public_sector_supplier_burden",
            category="governance",
            title="Public-sector supplier burden stack",
            severity=5,
            rationale="Multiple buyer/public-authority-favourable terms combine into cumulative supplier burden rather than isolated clause exposure.",
            why_it_matters="Cumulative burden: indemnity, termination, set-off, step-in, delivery, damages, FOIA, or procurement controls may compound supplier-side exposure.",
            triggered_by=matched_public_burden,
            contributors=contributors,
            reason="Three or more public-sector supplier burden signals were detected in the same reviewed text.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    matched_financial_exposure = sorted(matched_rule_ids.intersection(_SUPPLIER_PERFORMANCE_FINANCIAL_EXPOSURE_RULE_IDS))
    if len(matched_financial_exposure) >= 2:
        contributors = _first_contributors(by_rule_id, matched_financial_exposure)
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="cross_supplier_performance_financial_exposure",
            rule_id="cross_supplier_performance_financial_exposure",
            category="liability",
            title="Supplier performance-linked financial exposure stack",
            severity=5 if len(matched_financial_exposure) >= 3 else 4,
            rationale="Performance-linked deductions, damages, set-off, indemnity, strict delivery, step-in, or completion-cost recovery can compound financial exposure for the supplier.",
            why_it_matters="Financial exposure: multiple performance remedies may apply together, affecting margin, cash flow, and termination economics.",
            triggered_by=matched_financial_exposure,
            contributors=contributors,
            reason="At least two performance-linked financial exposure signals were detected in the same reviewed text.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    matched_public_data = sorted(matched_rule_ids.intersection(_DATA_PUBLIC_AUTHORITY_DISCLOSURE_RULE_IDS))
    if len(matched_public_data) >= 2:
        contributors = _first_contributors(by_rule_id, matched_public_data)
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="cross_data_public_authority_disclosure_stack",
            rule_id="cross_data_public_authority_disclosure_stack",
            category="data",
            title="Data and public-authority disclosure stack",
            severity=4,
            rationale="Outdated data protection, processing obligations, audit rights, and public-authority disclosure overrides require targeted review when they appear together.",
            why_it_matters="Data/confidentiality exposure: public disclosure duties and data handling obligations may interact in ways that weaken confidentiality expectations or update obligations.",
            triggered_by=matched_public_data,
            contributors=contributors,
            reason="At least two data, audit, FOIA, or public-authority disclosure signals were detected in the same reviewed text.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    if (upfront_text or matched_upfront) and (matched_suspension or suspension_text):
        triggered_by = matched_upfront + matched_suspension + upfront_text + suspension_text
        contributors = _first_contributors(by_rule_id, matched_upfront + matched_suspension)
        stronger = bool(matched_suspension) and (
            "disputed sums suspension" in suspension_text
            or "immediate suspension" in suspension_text
            or "service_suspension_right" in matched_suspension
        )
        added = _add_controlled_cross_clause_pattern(
            cross_findings=cross_findings,
            cross_adjustments=cross_adjustments,
            existing_rule_ids=existing_rule_ids,
            pattern="upfront_payment_suspension",
            rule_id="cross_upfront_payment_suspension",
            category="payment",
            title="Upfront payment combined with supplier suspension rights may create operational exposure",
            severity=5 if stronger else 4,
            rationale="A buyer may pay early while the supplier retains broad rights to suspend service, including for disputed, minor, or unresolved payment issues.",
            why_it_matters="Operational exposure: early cash outflow may remain at risk if service continuity can still be interrupted.",
            triggered_by=triggered_by,
            contributors=contributors,
            reason="Upfront or prepaid payment signals combine with broad supplier suspension rights.",
            remaining_score_room=remaining_score_room,
        )
        remaining_score_room -= added

    return cross_findings, cross_adjustments


def apply_cross_clause_synthesis(
    text: str,
    findings: List[Dict[str, Any]],
    matched_rule_ids: set[str],
    raw_matched_rule_ids: set[str],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    existing_findings, existing_adjustments = _build_cross_clause_findings(
        findings,
        matched_rule_ids,
        raw_matched_rule_ids,
    )
    combined_rule_ids = matched_rule_ids.union(
        {str(finding.get("rule_id", "")) for finding in existing_findings}
    )
    controlled_findings, controlled_adjustments = _build_controlled_cross_clause_findings(
        text,
        findings,
        combined_rule_ids,
    )
    return existing_findings + controlled_findings, existing_adjustments + controlled_adjustments

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

    matched_payment_leverage = sorted(matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS))
    if len(matched_payment_leverage) >= 2:
        contributors = [by_rule_id[rid][0] for rid in matched_payment_leverage if rid in by_rule_id]
        cross_findings.append(
            _derived_finding(
                rule_id="cross_payment_leverage_stack",
                category="payment",
                title="Stacked cashflow pressure and enforcement leverage",
                severity=4,
                weight=2,
                rationale="Multiple payment-pressure clauses appear together, creating stacked cashflow pressure and enforcement leverage beyond a single invoice-timing term.",
                triggered_by=matched_payment_leverage,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_payment_leverage_stack",
                "effect": 2,
                "reason": "Short payment timing, suspension leverage, and fee-acceleration or penalty terms may combine to create stronger cashflow pressure than any single clause alone.",
                "triggered_by": matched_payment_leverage,
            }
        )

    matched_payment_exit = sorted(matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS))
    matched_exit_pressure = sorted(matched_rule_ids.intersection(_EXIT_PRESSURE_SIGNAL_RULE_IDS))
    if matched_payment_exit and matched_exit_pressure:
        triggered_by = matched_payment_exit + matched_exit_pressure
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_exit_pressure = "cross_payment_leverage_stack" in matched_payment_exit
        effect = 2 if stronger_exit_pressure else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_payment_exit_pressure",
                category="payment",
                title="Payment pressure with constrained exit flexibility",
                severity=4 if stronger_exit_pressure else 3,
                weight=effect,
                rationale="Payment pressure is amplified because the customer also faces weak, delayed, or commercially constrained exit routes.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_payment_exit_pressure",
                "effect": effect,
                "reason": "Payment leverage combined with renewal, termination, or exit pressure can make the customer more exposed to continued spend or operational disruption.",
                "triggered_by": triggered_by,
            }
        )

    matched_variation = sorted(matched_rule_ids.intersection(_VARIATION_RULE_IDS))
    matched_variation_payment = sorted(matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS))
    if matched_variation and matched_variation_payment:
        triggered_by = matched_variation + matched_variation_payment
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_variation_payment = (
            "unilateral_amendment_policy_reference" in matched_variation
            or "cross_payment_leverage_stack" in matched_variation_payment
        )
        effect = 2 if stronger_variation_payment else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_variation_payment_leverage",
                category="payment",
                title="Variation rights with payment leverage",
                severity=4 if stronger_variation_payment else 3,
                weight=effect,
                rationale="The counterparty appears able to change commercial terms while payment pressure and service-continuity leverage remain in place, which can weaken practical resistance to the change package.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_variation_payment_leverage",
                "effect": effect,
                "reason": "Variation rights paired with payment pressure can reduce practical leverage if resisting the revised terms risks default, suspension, or accelerated payment exposure.",
                "triggered_by": triggered_by,
            }
        )

    matched_suspension_support = sorted(matched_rule_ids.intersection(_PAYMENT_SUPPORT_RULE_IDS))
    if "service_suspension_right" in matched_rule_ids and matched_suspension_support:
        triggered_by = ["service_suspension_right"] + [rid for rid in matched_suspension_support if rid != "service_suspension_right"]
        contributors = [by_rule_id[rid][0] for rid in dict.fromkeys(triggered_by) if rid in by_rule_id]
        nonstack_suspension_support = [rid for rid in matched_suspension_support if rid != "cross_payment_leverage_stack"]
        stronger_suspension_control = len(nonstack_suspension_support) >= 2
        effect = 0 if "cross_payment_leverage_stack" in matched_suspension_support else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_suspension_payment_control",
                category="payment",
                title="Suspension leverage tied to payment control",
                severity=4 if stronger_suspension_control or "cross_payment_leverage_stack" in matched_suspension_support else 3,
                weight=max(effect, 1),
                rationale="Operational continuity may be used as leverage where suspension rights sit alongside short deadlines, penalty exposure, or other payment-control clauses.",
                triggered_by=list(dict.fromkeys(triggered_by)),
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_suspension_payment_control",
                "effect": effect,
                "reason": "Suspension rights combined with surrounding payment-control language can make service continuity a pressure point in billing or default scenarios.",
                "triggered_by": list(dict.fromkeys(triggered_by)),
            }
        )

    matched_control_rights = sorted(matched_rule_ids.intersection(_CONTROL_RIGHT_RULE_IDS))
    non_variation_controls = [rid for rid in matched_control_rights if rid not in _VARIATION_RULE_IDS]
    if matched_exit_pressure and len(matched_control_rights) >= 2 and non_variation_controls:
        triggered_by = matched_control_rights + matched_exit_pressure
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_control_asymmetry = len(matched_control_rights) >= 3 or "service_suspension_right" in matched_control_rights
        effect = 2 if stronger_control_asymmetry else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_control_without_reciprocal_exit",
                category="termination",
                title="Counterparty control with weak reciprocal exit",
                severity=4 if stronger_control_asymmetry else 3,
                weight=effect,
                rationale="Multiple counterparty control rights appear alongside constrained exit routes, which can increase operational dependency before the customer can disengage on balanced terms.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_control_without_reciprocal_exit",
                "effect": effect,
                "reason": "Control-heavy clauses combined with weak reciprocal exit can create asymmetric dependency that is more commercially significant than the individual rights viewed in isolation.",
                "triggered_by": triggered_by,
            }
        )

    matched_auto_renewal_trap = sorted(matched_rule_ids.intersection(_RENEWAL_EXIT_TRAP_RULE_IDS))
    matched_hard_exit_lockin = sorted(matched_rule_ids.intersection(_HARD_EXIT_LOCKIN_RULE_IDS))
    if matched_auto_renewal_trap and matched_hard_exit_lockin and ("auto_renewal_silent" in matched_auto_renewal_trap or "auto_renewal_notice_trap" in matched_auto_renewal_trap):
        triggered_by = matched_auto_renewal_trap + matched_hard_exit_lockin
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_notice_trap = any(rid in {"auto_renewal_notice_trap", "renewal_long_commitment"} for rid in matched_auto_renewal_trap)
        effect = 2 if stronger_notice_trap or len(matched_hard_exit_lockin) >= 2 else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_auto_renewal_notice_exit_trap",
                category="renewal",
                title="Auto-renewal notice trap with constrained exit",
                severity=4 if effect == 2 else 3,
                weight=effect,
                rationale="Auto-renewal mechanics appear alongside constrained exit rights or exit-cost terms, which may keep the customer bound if notice timing is missed.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_auto_renewal_notice_exit_trap",
                "effect": effect,
                "reason": "Auto-renewal notice mechanics combined with constrained exit rights can turn a missed renewal date into a fresh lock-in event.",
                "triggered_by": triggered_by,
            }
        )

    matched_renewal_economic_change = sorted(matched_rule_ids.intersection(_RENEWAL_ECONOMIC_CHANGE_RULE_IDS))
    if matched_auto_renewal_trap and matched_hard_exit_lockin and matched_renewal_economic_change:
        triggered_by = matched_auto_renewal_trap + matched_renewal_economic_change + matched_hard_exit_lockin
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_renewal_price_exit = (
            "renewal_price_increase_on_renewal" in matched_renewal_economic_change
            or len(matched_hard_exit_lockin) >= 2
        )
        effect = 2 if stronger_renewal_price_exit else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_renewal_price_exit_trap",
                category="renewal",
                title="Renewal price change with constrained exit",
                severity=4 if effect == 2 else 3,
                weight=effect,
                rationale="Renewal-related economic change appears alongside constrained exit mechanics, which may roll the customer into changed pricing before there is practical room to disengage.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_renewal_price_exit_trap",
                "effect": effect,
                "reason": "Renewal pricing change combined with weak exit rights can increase the chance of rolling into a more expensive contract before the customer can respond effectively.",
                "triggered_by": triggered_by,
            }
        )

    matched_exit_cost = sorted(matched_rule_ids.intersection(_EXIT_COST_RULE_IDS))
    matched_weak_customer_exit = sorted(matched_rule_ids.intersection(_HARD_EXIT_LOCKIN_RULE_IDS.union({"auto_renewal_notice_trap", "renewal_long_commitment"})))
    if matched_exit_cost and matched_weak_customer_exit:
        triggered_by = matched_exit_cost + matched_weak_customer_exit
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_fee_lockin = any(rid in {"early_termination_fee", "minimum_commitment_lock_in"} for rid in matched_exit_cost)
        effect = 2 if stronger_fee_lockin and len(matched_weak_customer_exit) >= 1 else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_termination_fee_lock_in",
                category="termination",
                title="Exit cost with weak termination flexibility",
                severity=4 if effect == 2 else 3,
                weight=effect,
                rationale="The contract appears to allow exit only at meaningful cost or with constrained flexibility, which can make leaving commercially prohibitive even where termination is technically available.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_termination_fee_lock_in",
                "effect": effect,
                "reason": "Exit-cost clauses paired with weak customer exit rights can make the practical cost of disengagement materially higher than a simple termination label suggests.",
                "triggered_by": triggered_by,
            }
        )

    matched_supplier_control = sorted(matched_rule_ids.intersection(_CONTROL_RIGHT_RULE_IDS.union(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS)))
    if len(matched_supplier_control) >= 2 and matched_hard_exit_lockin:
        triggered_by = matched_supplier_control + matched_hard_exit_lockin
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger_supplier_control = len(matched_supplier_control) >= 3 or "cross_payment_leverage_stack" in matched_supplier_control
        effect = 2 if stronger_supplier_control else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_supplier_control_customer_lock_in",
                category="termination",
                title="Supplier control with customer lock-in",
                severity=4 if effect == 2 else 3,
                weight=effect,
                rationale="Broad supplier control rights appear alongside customer lock-in features, increasing the risk that operational or commercial changes can be imposed while exit remains constrained.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_supplier_control_customer_lock_in",
                "effect": effect,
                "reason": "Supplier control rights combined with customer lock-in can create asymmetric dependency beyond the effect of the underlying clauses viewed separately.",
                "triggered_by": triggered_by,
            }
        )

    exit_trap_dimensions = 0
    if matched_auto_renewal_trap:
        exit_trap_dimensions += 1
    if any(rid in {"renewal_notice_window_pressure", "auto_renewal_notice_trap", "renewal_long_commitment"} for rid in matched_auto_renewal_trap):
        exit_trap_dimensions += 1
    if matched_renewal_economic_change:
        exit_trap_dimensions += 1
    if matched_exit_cost:
        exit_trap_dimensions += 1
    if matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS):
        exit_trap_dimensions += 1
    if matched_hard_exit_lockin:
        exit_trap_dimensions += 1
    if exit_trap_dimensions >= 3 and matched_hard_exit_lockin and matched_auto_renewal_trap:
        triggered_pool = set(matched_auto_renewal_trap + matched_renewal_economic_change + matched_exit_cost + matched_hard_exit_lockin + sorted(matched_rule_ids.intersection(_PAYMENT_LEVERAGE_SIGNAL_RULE_IDS)))
        triggered_by = sorted(triggered_pool)
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        effect = 3 if exit_trap_dimensions >= 5 else 2
        cross_findings.append(
            _derived_finding(
                rule_id="cross_exit_trap_stack",
                category="termination",
                title="Structural renewal and exit trap stack",
                severity=5 if effect == 3 else 4,
                weight=effect,
                rationale="Multiple lock-in dimensions appear together across renewal, pricing, payment, and exit clauses, suggesting a structural exit trap rather than a single isolated term.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_exit_trap_stack",
                "effect": effect,
                "reason": "Several renewal, exit-cost, payment, and control dimensions combine into a broader lock-in structure that deserves consolidated review before acceptance or renewal.",
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

    matched_audit = sorted(matched_rule_ids.intersection(_AUDIT_GOVERNANCE_RULE_IDS))
    matched_data_governance = sorted(matched_rule_ids.intersection(_DATA_GOVERNANCE_RULE_IDS))
    matched_confidentiality = sorted(matched_rule_ids.intersection(_CONFIDENTIALITY_WEAKNESS_RULE_IDS))
    if matched_audit and matched_data_governance and matched_confidentiality:
        triggered_by = list(dict.fromkeys(matched_audit + matched_data_governance + matched_confidentiality))
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        effect = 1 if len(triggered_by) <= 3 else 2
        cross_findings.append(
            _derived_finding(
                rule_id="cross_audit_data_confidentiality_exposure",
                category="audit",
                title="Audit access with data and confidentiality exposure",
                severity=4,
                weight=effect,
                rationale="Broad audit access appears alongside data-governance and confidentiality-survival weaknesses, creating governance/data exposure that may require coordinated operational review.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_audit_data_confidentiality_exposure",
                "effect": effect,
                "reason": "Audit rights that reach data or systems become more significant when data-transfer, retention, or confidentiality-survival controls are also weak.",
                "triggered_by": triggered_by,
            }
        )

    matched_change_control = sorted(matched_rule_ids.intersection(_CHANGE_CONTROL_RULE_IDS))
    matched_weak_remedies = sorted(matched_rule_ids.intersection(_WEAK_SERVICE_REMEDY_RULE_IDS))
    has_structural_change_remedy = (
        "unilateral_change_control_scope_terms" in matched_change_control
        or any(rid in matched_weak_remedies for rid in {"weak_sla_service_remedy_suspension", "service_credits_sole_remedy", "exclusive_remedy_limitation"})
    )
    if matched_change_control and matched_weak_remedies and has_structural_change_remedy:
        triggered_by = list(dict.fromkeys(matched_change_control + matched_weak_remedies))
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        stronger = "unilateral_change_control_scope_terms" in matched_change_control and len(matched_weak_remedies) >= 2
        effect = 2 if stronger else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_change_control_weak_remedies",
                category="amendment",
                title="Unilateral change control with weak remedies",
                severity=4 if stronger else 3,
                weight=effect,
                rationale="Unilateral change-control language appears alongside weak service-level or remedy terms, which can create supplier control imbalance and reduce practical recourse.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_change_control_weak_remedies",
                "effect": effect,
                "reason": "Change rights become more commercially significant when the remedy package gives limited protection for degraded service, altered scope, or operational disruption.",
                "triggered_by": triggered_by,
            }
        )

    matched_ip_controls = sorted(matched_rule_ids.intersection(_IP_ASSET_CONTROL_RULE_IDS))
    if "ip_ownership_foreground_conflict" in matched_ip_controls and "ip_broad_license_or_residuals" in matched_ip_controls:
        triggered_by = matched_ip_controls
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        cross_findings.append(
            _derived_finding(
                rule_id="cross_ip_asset_leakage",
                category="ip",
                title="IP ownership and licence leakage stack",
                severity=5,
                weight=2,
                rationale="Foreground ownership conflict appears together with broad licence, derivative, or residual-knowledge language, creating strategic asset-control risk without drawing enforceability conclusions.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_ip_asset_leakage",
                "effect": 2,
                "reason": "IP ownership conflict is more significant when licence scope or residual-knowledge rights also point toward possible asset leakage.",
                "triggered_by": triggered_by,
            }
        )

    matched_force_majeure = "force_majeure_broad_or_prolonged" in matched_rule_ids
    matched_fm_weak_exit = sorted(matched_rule_ids.intersection(_FORCE_MAJEURE_WEAK_EXIT_RULE_IDS))
    if matched_force_majeure and matched_fm_weak_exit:
        triggered_by = list(dict.fromkeys(["force_majeure_broad_or_prolonged"] + matched_fm_weak_exit))
        contributors = [by_rule_id[rid][0] for rid in triggered_by if rid in by_rule_id]
        effect = 2 if len(matched_fm_weak_exit) >= 2 else 1
        cross_findings.append(
            _derived_finding(
                rule_id="cross_force_majeure_continuity_lock_in",
                category="force_majeure",
                title="Force majeure suspension with weak exit",
                severity=4,
                weight=effect,
                rationale="Broad or prolonged force majeure relief appears alongside constrained exit mechanics, creating continuity lock-in and performance-accountability exposure.",
                triggered_by=triggered_by,
                contributors=contributors,
            )
        )
        cross_adjustments.append(
            {
                "type": "compound_risk",
                "rule_id": "cross_force_majeure_continuity_lock_in",
                "effect": effect,
                "reason": "Force majeure suspension or relief carries more operational risk where termination or transition options are also constrained.",
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


def _top_risk_rank_key(f: Dict[str, Any]) -> Tuple[int, int, int, int, int, int, int, str]:
    rule_id = str(f.get("rule_id", ""))
    category = str(f.get("category", ""))
    matched_text = _normalize_ws(str(f.get("matched_text", "")))
    excerpt = _normalize_ws(str(f.get("excerpt", "")))
    evidence_len = max(len(matched_text), len(excerpt))
    structural_bonus = 1 if rule_id in _TOP_RISK_STRUCTURAL_RULE_IDS else 0
    material_data_bonus = 1 if rule_id in _TOP_RISK_MATERIAL_DATA_RULE_IDS else 0
    category_bonus = _TOP_RISK_CATEGORY_PRIORITY.get(category, 2)
    thin_penalty = 1 if rule_id in _TOP_RISK_THIN_SIGNAL_RULE_IDS and len(matched_text) <= 20 else 0

    return (
        int(f.get("severity", 1)),
        structural_bonus,
        material_data_bonus,
        category_bonus,
        int(f.get("weight", 0)),
        evidence_len,
        -thin_penalty,
        str(f.get("title", "")),
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


def _contextual_emphasis_for_finding(
    finding: Dict[str, Any],
    context_profile: Dict[str, Any],
) -> Optional[str]:
    context = context_profile.get("context", {}) or {}
    role = context.get("user_role", "unknown")
    contract_type = context.get("contract_type", "unknown")
    criticality = context.get("value_criticality", "unknown")
    category = str(finding.get("category", ""))
    rule_id = str(finding.get("rule_id", ""))

    if role == "buyer" and (category in {"service", "payment", "termination"} or "suspension" in rule_id):
        return "Buyer context: review operational continuity, cash-flow exposure, and supplier control leverage before acceptance."

    if role in {"supplier", "saas_provider", "consultant", "agency"} and category in {"liability", "indemnity"}:
        return "Supplier context: review downside exposure, insurability, and margin protection before accepting this allocation."

    if contract_type in {"saas", "data_processing", "healthcare"} and category in {"data", "confidentiality", "licensing"}:
        return "Data-heavy context: review governance, confidentiality, onward transfer, and trust impact before relying on the clause package."

    if criticality in {"high_value", "business_critical", "strategic_partnership"}:
        return "Criticality context: evidence-backed escalation should be stronger because operational or financial consequence may be material."

    if criticality in {"low_value", "one_off", "pilot"}:
        return "Limited-criticality context: keep the finding visible, but calibrate escalation to the deal value and dependency."

    return None


def _apply_contextual_emphasis(
    findings: List[Dict[str, Any]],
    context_profile: Dict[str, Any],
) -> None:
    for finding in findings:
        emphasis = _contextual_emphasis_for_finding(finding, context_profile)
        if emphasis:
            finding["contextual_emphasis"] = emphasis


def score_contract(
    text: str,
    *,
    include_findings: bool = True,
    include_meta: bool = True,
    risk_appetite: str = "balanced",
    jurisdiction: Optional[str] = None,
    sector: Optional[str] = None,
    contract_type: Optional[str] = None,
    user_role: Optional[str] = None,
    counterparty_profile: Optional[str] = None,
    value_criticality: Optional[str] = None,
    document_position: Optional[str] = None,
    objective: Optional[str] = None,
    policy_profile: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context_profile = build_context_profile_metadata(
        jurisdiction=jurisdiction,
        sector=sector,
        contract_type=contract_type,
        user_role=user_role,
        counterparty_profile=counterparty_profile,
        value_criticality=value_criticality,
        document_position=document_position,
        objective=objective,
    )
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

    cross_findings, cross_adjustments = apply_cross_clause_synthesis(
        scan_text,
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

    sector_playbooks = _infer_sector_playbooks(scan_text, matched_rule_ids)
    sector_findings, sector_adjustments = _build_sector_synthesis_findings(
        scan_text,
        deduped_findings,
        matched_rule_ids,
        sector_playbooks,
    )
    if sector_adjustments:
        adjusted_risk_score += sum(int(adj.get("effect", 0)) for adj in sector_adjustments)
        score_adjustments.extend(sector_adjustments)
    if sector_findings:
        deduped_findings.extend(sector_findings)
        matched_rule_ids = {str(f["rule_id"]) for f in deduped_findings}

    adjusted_risk_score, selected_risk_appetite, appetite_adjustments = _apply_risk_appetite(
        adjusted_risk_score,
        deduped_findings,
        risk_appetite,
    )
    if appetite_adjustments:
        score_adjustments.extend(appetite_adjustments)

    _apply_contextual_emphasis(deduped_findings, context_profile)

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
    synthesis_patterns_triggered = sorted(
        {
            str(adj.get("pattern"))
            for adj in score_adjustments
            if adj.get("type") == "cross_clause" and adj.get("pattern")
        }
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
    top_ranked_findings = sorted(
        deduped_findings,
        key=_top_risk_rank_key,
        reverse=True,
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
            "rule_families_detected": sorted({str(f.get("category", "")) for f in deduped_findings if str(f.get("category", ""))}),
            "sector_playbooks": sector_playbooks,
            "context_profile_used": context_profile,
            "context_confidence": context_profile.get("context_confidence"),
            "context_limitations": context_profile.get("context_limitations", []),
            "context_emphasis": context_profile.get("context_emphasis", []),
            "risk_appetite": selected_risk_appetite,
            "risk_appetite_adjustments": appetite_adjustments,
            "synthesis_patterns_triggered": synthesis_patterns_triggered,
            "derived_finding_count": sum(1 for f in deduped_findings if str(f.get("matched_pattern", "")).startswith("derived_")),
            "confidence_driver": "No governed rule match detected in reviewed text" if not deduped_findings else None,
            "signal_type": "Low-signal automated review" if not deduped_findings else "Structural clause-level exposure",
            "primary_risk_type": "No elevated rule signal" if not deduped_findings else "Contract risk signal",
            "reliability_wording": "Extraction completed; no covered rule signal detected" if not deduped_findings else None,
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
            for f in top_ranked_findings[:3]
        ]
        if overlap_suppressions:
            result["meta"]["overlap_suppressions"] = overlap_suppressions

    if policy_profile is not None:
        apply_policy_to_payload(result, policy_profile)

    return result


def score_text(text: str):
    return score_contract(text)
