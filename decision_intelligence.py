from __future__ import annotations

from collections import Counter
from datetime import date
from typing import Any

POLICY_METADATA = {
    "version": "2026.05.phase3",
    "last_updated": "2026-05-01",
    "change_note": "Initial organisation tolerance and policy comparison foundation.",
}

DECISION_METADATA = {
    "version": "2026.05.phase4",
    "last_updated": "2026-05-01",
    "change_note": "Initial organisation-scoped decision path and outcome memory foundation.",
}

INTELLIGENCE_METADATA = {
    "version": "2026.05.phase5",
    "last_updated": "2026-05-01",
    "change_note": "Initial organisation-scoped decision intelligence foundation without aggregate market claims.",
}

ALLOWED_POLICY_VALUES: dict[str, set[str]] = {
    "unlimited_liability": {"always_escalate", "sometimes_accept", "accept_if_mutual", "accept_only_with_cap", "unknown"},
    "auto_renewal": {"allow", "require_notice", "always_flag", "allow_only_with_exit_window", "unknown"},
    "unilateral_price_increase": {"reject", "negotiate", "tolerate_with_cap", "allow_with_termination_right", "unknown"},
    "governing_law_forum_mismatch": {"escalate", "accept_if_low_value", "case_by_case", "approved_jurisdictions_only", "unknown"},
    "broad_indemnity": {"escalate", "negotiate", "allow_if_capped", "allow_if_mutual", "unknown"},
    "data_use": {"strict", "moderate", "flexible", "no_ai_training", "no_onward_sharing", "unknown"},
}

DEFAULT_ORG_POLICY: dict[str, str] = {key: "unknown" for key in ALLOWED_POLICY_VALUES}

SCAN_DECISION_STATES = {
    "pending",
    "accepted",
    "negotiated",
    "escalated",
    "rejected",
    "sent_for_legal_review",
}

FINDING_DECISION_STATUSES = {
    "unresolved",
    "accepted",
    "redlined",
    "waived",
    "escalated",
    "ignored",
}

DECISION_REASON_CODES = {
    "commercial_exception",
    "low_value_contract",
    "strategic_relationship",
    "legal_review_required",
    "insurer_requirement",
    "procurement_policy",
    "customer_requirement",
    "supplier_non_negotiable",
    "corrected_in_redline",
    "accepted_with_awareness",
    "other",
}

SECTOR_INTELLIGENCE_PACKS: dict[str, dict[str, Any]] = {
    "SaaS": {
        "label": "SaaS",
        "supported_risk_families": ["data use", "liability", "termination", "suspension", "auto-renewal"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "agencies": {
        "label": "Agencies",
        "supported_risk_families": ["payment", "scope", "liability", "termination", "intellectual property"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "consulting": {
        "label": "Consulting",
        "supported_risk_families": ["liability", "indemnity", "payment", "confidentiality", "termination"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "procurement": {
        "label": "Procurement",
        "supported_risk_families": ["payment", "price variation", "suspension", "subcontracting", "jurisdiction"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "healthcare": {
        "label": "Healthcare",
        "supported_risk_families": ["data use", "confidentiality", "liability", "subcontracting", "service"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "security_services": {
        "label": "Security services",
        "supported_risk_families": ["liability", "service", "suspension", "termination", "indemnity"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "data_processing": {
        "label": "Data processing",
        "supported_risk_families": ["data use", "confidentiality", "subcontracting", "jurisdiction"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
}

AGGREGATE_INSIGHTS_GOVERNANCE = {
    "aggregate_insights_enabled": False,
    "anonymisation_required": True,
    "customer_contract_text_excluded": True,
    "release_ready": False,
}


def validate_policy_values(policy: dict[str, Any]) -> dict[str, str]:
    validated: dict[str, str] = {}
    for key, raw_value in policy.items():
        if key not in ALLOWED_POLICY_VALUES:
            raise ValueError(f"unsupported policy key: {key}")
        value = str(raw_value or "unknown").strip().lower()
        if value not in ALLOWED_POLICY_VALUES[key]:
            raise ValueError(f"unsupported policy value for {key}")
        validated[key] = value
    return validated


def normalize_policy(policy: dict[str, Any] | None) -> dict[str, str]:
    normalized = dict(DEFAULT_ORG_POLICY)
    if policy:
        for key, value in policy.items():
            candidate = str(value or "unknown")
            if key in ALLOWED_POLICY_VALUES and candidate in ALLOWED_POLICY_VALUES[key]:
                normalized[key] = candidate
    return normalized


def finding_policy_category(finding: dict[str, Any]) -> str | None:
    category = str(finding.get("category") or "").lower()
    rule_id = str(finding.get("rule_id") or finding.get("id") or "").lower()
    title = str(finding.get("title") or "").lower()
    haystack = f"{category} {rule_id} {title}"
    if "unlimited" in haystack and "liability" in haystack:
        return "unlimited_liability"
    if ("auto" in haystack and "renew" in haystack) or "renewal" in haystack:
        return "auto_renewal"
    if "price" in haystack or "fee increase" in haystack or "unilateral_price" in haystack:
        return "unilateral_price_increase"
    if category == "jurisdiction" or "forum" in haystack or "governing_law" in haystack:
        return "governing_law_forum_mismatch"
    if "indemn" in haystack:
        return "broad_indemnity"
    if category in {"data", "licensing"} or "data" in haystack or "ai training" in haystack:
        return "data_use"
    return None


def _finding_text(finding: dict[str, Any]) -> str:
    parts = [
        finding.get("title"),
        finding.get("rule_id"),
        finding.get("category"),
        finding.get("matched_text"),
        finding.get("rationale"),
        finding.get("contextual_emphasis"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _policy_result(category: str, value: str, finding: dict[str, Any]) -> tuple[str, str]:
    text = _finding_text(finding)
    if value == "unknown":
        return "policy_unknown", "Policy unknown: no tolerance configured for this risk family. Evidence should still be documented."

    if category == "broad_indemnity":
        if value == "escalate":
            return "exceeds_tolerance", "Broad indemnity exceeds your stated tolerance and should be escalated."
        if value == "negotiate":
            return "conflicts_with_policy", "Broad indemnity conflicts with your usual position unless narrowed in negotiation."
        if value == "allow_if_capped":
            if "cap" in text and "uncapped" not in text:
                return "within_tolerance", "Within configured tolerance if the indemnity is genuinely capped; preserve the evidence."
            return "conflicts_with_policy", "Broad indemnity is outside your normal acceptance range unless capped."
        if value == "allow_if_mutual":
            if "mutual" in text or "reciprocal" in text:
                return "within_tolerance", "Within configured tolerance if the indemnity is genuinely mutual; preserve the evidence."
            return "conflicts_with_policy", "Broad indemnity conflicts with policy because mutual protection is not apparent."

    if category == "data_use":
        if value == "strict":
            return "exceeds_tolerance", "Broad data-use permissions exceed your strict data governance posture."
        if value == "moderate":
            return "conflicts_with_policy", "Data-use permissions require management review against your moderate governance posture."
        if value == "flexible":
            return "within_tolerance", "Within configured tolerance, but data-use evidence should still be documented."
        if value == "no_ai_training":
            if "ai" in text or "training" in text or "machine learning" in text or "any purpose" in text or "service improvement" in text:
                return "exceeds_tolerance", "Data-use permissions exceed your policy because AI training, model use, or broad training-compatible use appears."
            return "within_tolerance", "Within configured tolerance where AI training is not apparent; preserve the evidence."
        if value == "no_onward_sharing":
            if "onward" in text or "sublicens" in text or "transfer" in text or "disclos" in text:
                return "exceeds_tolerance", "Data-use permissions exceed your policy because onward sharing or transfer appears."
            return "within_tolerance", "Within configured tolerance where onward sharing is not apparent; preserve the evidence."

    if category == "auto_renewal":
        if value == "allow":
            return "within_tolerance", "Within configured renewal tolerance, but notice evidence should still be documented."
        if value == "require_notice":
            if "notice" in text:
                return "within_tolerance", "Within configured tolerance if the renewal notice period is operationally usable."
            return "conflicts_with_policy", "This renewal structure conflicts with your usual renewal policy because clear notice is not apparent."
        if value == "always_flag":
            return "exceeds_tolerance", "Auto-renewal exceeds your stated tolerance and should remain flagged."
        if value == "allow_only_with_exit_window":
            if "exit" in text or "terminate" in text or "cancel" in text:
                return "within_tolerance", "Within configured tolerance if the exit window is practical and documented."
            return "conflicts_with_policy", "Auto-renewal conflicts with policy because an exit window is not apparent."

    if category == "unilateral_price_increase":
        if value == "reject":
            return "exceeds_tolerance", "Unilateral price increase rights exceed your stated tolerance."
        if value == "negotiate":
            return "conflicts_with_policy", "Unilateral price increase rights conflict with your usual policy unless negotiated."
        if value == "tolerate_with_cap":
            if "cap" in text or "%" in text:
                return "within_tolerance", "Within configured tolerance if the price increase cap is effective and documented."
            return "conflicts_with_policy", "This pricing structure conflicts with policy because a cap is not apparent."
        if value == "allow_with_termination_right":
            if "terminate" in text or "termination" in text:
                return "within_tolerance", "Within configured tolerance if the termination right is practical and documented."
            return "conflicts_with_policy", "This pricing structure conflicts with policy because a termination right is not apparent."

    if category == "unlimited_liability":
        if value == "always_escalate":
            return "exceeds_tolerance", "Unlimited liability exceeds your stated tolerance and should be escalated."
        if value == "sometimes_accept":
            return "conflicts_with_policy", "Unlimited liability requires documented commercial rationale before acceptance."
        if value == "accept_if_mutual":
            if "mutual" in text or "reciprocal" in text:
                return "within_tolerance", "Within configured tolerance if unlimited liability is genuinely mutual; preserve the evidence."
            return "conflicts_with_policy", "Unlimited liability conflicts with policy because mutuality is not apparent."
        if value == "accept_only_with_cap":
            return "exceeds_tolerance", "Unlimited liability is outside your normal acceptance range unless capped."

    if category == "governing_law_forum_mismatch":
        if value == "escalate":
            return "exceeds_tolerance", "Jurisdiction or forum mismatch exceeds your stated tolerance and should be escalated."
        if value == "accept_if_low_value":
            return "conflicts_with_policy", "Jurisdiction or forum mismatch requires value-based review before acceptance."
        if value == "case_by_case":
            return "conflicts_with_policy", "Jurisdiction or forum mismatch requires case-by-case management review."
        if value == "approved_jurisdictions_only":
            return "conflicts_with_policy", "Jurisdiction or forum mismatch conflicts with policy unless it is on the approved list."

    return "policy_unknown", "Policy unknown: no tolerance configured for this risk family. Evidence should still be documented."


def decision_guidance_for_finding(finding: dict[str, Any]) -> list[str]:
    category = finding_policy_category(finding)
    text = _finding_text(finding)
    guidance: list[str] = []
    if category == "unlimited_liability" or "liability" in text:
        guidance.append("cap liability")
    if category == "broad_indemnity":
        guidance.append("narrow indemnity")
    if category == "auto_renewal":
        guidance.extend(["add notice", "add exit right"])
    if category == "governing_law_forum_mismatch":
        guidance.append("align jurisdiction/forum")
    if category == "data_use":
        guidance.append("limit data use")
        if "ai" in text or "training" in text:
            guidance.append("remove AI training")
        if "onward" in text or "sublicens" in text or "sharing" in text or "transfer" in text:
            guidance.append("remove onward sharing")
    if "suspension" in text or "suspend" in text:
        guidance.extend(["add cure period", "limit suspension right"])
    if "refund" in text or "prepaid" in text or "non-refundable" in text:
        guidance.append("add refund/credit right")
    if "price" in text or "fee increase" in text:
        guidance.extend(["add notice", "add exit right"])
    return sorted(dict.fromkeys(guidance))


def apply_policy_to_payload(
    payload: dict[str, Any],
    policy: dict[str, Any] | None,
    *,
    prior_outcome_hint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_policy = normalize_policy(policy)
    findings = payload.get("findings") or []
    policy_counts: Counter[str] = Counter()
    breaches: Counter[str] = Counter()
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        policy_category = finding_policy_category(finding)
        if not policy_category:
            continue
        policy_value = normalized_policy.get(policy_category, "unknown")
        status, explanation = _policy_result(policy_category, policy_value, finding)
        finding["policy_category"] = policy_category
        finding["policy_value"] = policy_value
        finding["policy_status"] = status
        finding["policy_explanation"] = explanation
        finding["decision_guidance"] = decision_guidance_for_finding(finding)
        policy_counts[status] += 1
        if status in {"exceeds_tolerance", "conflicts_with_policy"}:
            breaches[policy_category] += 1

    meta = payload.setdefault("meta", {})
    meta["policy_profile_used"] = normalized_policy
    meta["policy_metadata"] = POLICY_METADATA
    meta["policy_status_summary"] = dict(policy_counts)
    meta["most_common_policy_breaches"] = [
        {"policy_category": key, "count": count} for key, count in breaches.most_common()
    ]
    meta["decision_intelligence"] = build_decision_intelligence_snapshot(
        payload,
        prior_outcome_hint=prior_outcome_hint,
    )
    return payload


def build_decision_intelligence_snapshot(
    payload: dict[str, Any],
    *,
    prior_outcome_hint: dict[str, Any] | None = None,
    decision_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    open_findings = [
        finding for finding in findings if finding.get("policy_status") in {"exceeds_tolerance", "conflicts_with_policy", "policy_unknown"}
    ]
    top_drivers = [
        {
            "rule_id": finding.get("rule_id"),
            "title": finding.get("title"),
            "category": finding.get("category"),
            "policy_category": finding.get("policy_category"),
            "policy_status": finding.get("policy_status"),
        }
        for finding in findings[:5]
    ]
    evidence_references = [
        {
            "rule_id": finding.get("rule_id"),
            "evidence_excerpt": finding.get("matched_text"),
        }
        for finding in findings[:5]
        if finding.get("matched_text")
    ]
    policy_summary = payload.get("meta", {}).get("policy_status_summary", {}) or {}
    posture = "Decision posture is pending; deterministic scoring remains the governing core."
    if prior_outcome_hint and prior_outcome_hint.get("state") and prior_outcome_hint.get("family"):
        posture = (
            f"Your organisation {prior_outcome_hint['state']} this type of risk in prior contracts; "
            "this scan follows the same pattern unless a commercial exception is recorded."
        )
    elif policy_summary.get("exceeds_tolerance"):
        posture = "One or more findings exceed configured tolerance and should be escalated or documented before acceptance."
    elif policy_summary.get("conflicts_with_policy"):
        posture = "One or more findings conflict with usual policy and should be negotiated or exception-tracked."
    elif policy_summary.get("policy_unknown"):
        posture = "Policy unknown for one or more findings; decision posture is conservative until tolerance is configured."

    return {
        "decision_posture": posture,
        "top_drivers": top_drivers,
        "evidence_references": evidence_references,
        "tolerance_comparison": policy_summary,
        "open_issues": [
            {
                "rule_id": finding.get("rule_id"),
                "title": finding.get("title"),
                "policy_status": finding.get("policy_status"),
                "decision_guidance": finding.get("decision_guidance", []),
            }
            for finding in open_findings[:10]
        ],
        "decision_log_summary": decision_summary or {"scan_state": "pending", "finding_status_default": "unresolved"},
        "policy_status_summary": policy_summary,
        "metadata": INTELLIGENCE_METADATA,
        "boundary_notice": "Decision intelligence supports management review only and is not legal advice or a legal-outcome engine.",
    }


def context_bucket_from_scan(scan_context: dict[str, Any] | None, key: str) -> str:
    if not scan_context:
        return "unknown"
    context = scan_context.get("context") if isinstance(scan_context.get("context"), dict) else scan_context
    return str((context or {}).get(key) or "unknown")


def today_iso() -> str:
    return date.today().isoformat()
