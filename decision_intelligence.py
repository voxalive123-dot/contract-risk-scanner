from __future__ import annotations

from collections import Counter
from datetime import date
import re
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
    "version": "2026.05.phase10",
    "last_updated": "2026-05-01",
    "change_note": "Organisation-scoped memory, governance, negotiation, sector, jurisdiction, and linked-document intelligence foundation without legal-outcome claims.",
}

OUTCOME_EVENT_CATEGORIES = {
    "accepted",
    "negotiated",
    "escalated",
    "rejected",
    "dispute",
    "payment_issue",
    "termination_event",
    "operational_incident",
    "renewal_issue",
    "compliance_issue",
}

DOCUMENT_RELATIONSHIP_TYPES = {
    "msa",
    "sow",
    "sla",
    "dpa",
    "amendment",
    "annexure",
    "purchase_order",
    "other",
}

ALLOWED_POLICY_VALUES: dict[str, set[str]] = {
    "unlimited_liability": {"always_escalate", "sometimes_accept", "accept_if_mutual", "accept_only_with_cap", "unknown"},
    "auto_renewal": {"allow", "require_notice", "always_flag", "allow_only_with_exit_window", "unknown"},
    "unilateral_price_increase": {"reject", "negotiate", "tolerate_with_cap", "allow_with_termination_right", "unknown"},
    "governing_law_forum_mismatch": {"escalate", "accept_if_low_value", "case_by_case", "approved_jurisdictions_only", "unknown"},
    "broad_indemnity": {"escalate", "negotiate", "allow_if_capped", "allow_if_mutual", "unknown"},
    "data_use": {"strict", "moderate", "flexible", "no_ai_training", "no_onward_sharing", "unknown"},
    "uncapped_indemnity": {"reject", "escalate", "negotiate", "unknown"},
    "deal_value_threshold": {"legal_review_over_250k", "executive_approval_over_250k", "legal_review_over_100k", "unknown"},
    "auto_renewal_duration": {"prohibit_over_12_months", "review_over_12_months", "allow", "unknown"},
    "eu_data_processing": {"require_dpa", "review", "unknown"},
    "cross_border_transfer": {"executive_approval", "review", "unknown"},
    "high_liability_exposure": {"insurance_required", "escalate", "unknown"},
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
    "saas": {
        "label": "SaaS",
        "supported_risk_families": ["data use", "liability", "termination", "suspension", "auto-renewal"],
        "caution_note": "Foundation only; sector pack does not make legal-outcome claims.",
        "release_ready": False,
    },
    "fintech": {
        "label": "Fintech",
        "supported_risk_families": ["data use", "confidentiality", "liability", "audit", "jurisdiction"],
        "caution_note": "Operational and compliance attention signal only; not regulatory advice.",
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
    "ai_vendors": {
        "label": "AI vendors",
        "supported_risk_families": ["data use", "confidentiality", "intellectual property", "liability", "audit"],
        "caution_note": "Operational AI-vendor review signal only; not regulatory or legal advice.",
        "release_ready": False,
    },
    "government": {
        "label": "Government",
        "supported_risk_families": ["termination", "step-in", "audit", "data use", "jurisdiction"],
        "caution_note": "Public-sector style attention signal only; not procurement law advice.",
        "release_ready": False,
    },
    "manufacturing": {
        "label": "Manufacturing",
        "supported_risk_families": ["delivery", "liability", "indemnity", "payment", "termination"],
        "caution_note": "Operational supply-chain attention signal only.",
        "release_ready": False,
    },
    "logistics": {
        "label": "Logistics",
        "supported_risk_families": ["delivery", "service", "liability", "suspension", "termination"],
        "caution_note": "Operational continuity attention signal only.",
        "release_ready": False,
    },
    "real_estate": {
        "label": "Real estate",
        "supported_risk_families": ["lease", "termination", "payment", "liability", "jurisdiction"],
        "caution_note": "Lease and property review attention signal only; not real-estate legal advice.",
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
        finding.get("excerpt"),
        finding.get("rationale"),
        finding.get("contextual_emphasis"),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _context_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    context_profile = meta.get("context_profile_used") if isinstance(meta.get("context_profile_used"), dict) else {}
    context = context_profile.get("context") if isinstance(context_profile.get("context"), dict) else {}
    return context or {}


def _parse_money(value: Any) -> float | None:
    if value is None:
        return None
    text = str(value).lower().strip()
    if not text:
        return None
    multiplier = 1.0
    if re.search(r"\b(?:m|mn|million)\b", text):
        multiplier = 1_000_000.0
    elif re.search(r"\b(?:k|thousand)\b", text):
        multiplier = 1_000.0
    match = re.search(r"(\d+(?:[,\s]\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)", text)
    if not match:
        return None
    numeric = re.sub(r"[,\s]", "", match.group(1))
    try:
        return float(numeric) * multiplier
    except ValueError:
        return None


def _finding_has_any(finding: dict[str, Any], needles: set[str]) -> bool:
    text = _finding_text(finding)
    return any(needle in text for needle in needles)


def _evidence_refs(findings: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        refs.append(
            {
                "rule_id": finding.get("rule_id"),
                "title": finding.get("title"),
                "evidence_excerpt": finding.get("matched_text") or finding.get("excerpt"),
            }
        )
        if len(refs) >= limit:
            break
    return refs


def _posture_rank(value: str) -> int:
    order = {
        "monitor only": 0,
        "acceptable below threshold": 1,
        "acceptable": 2,
        "acceptable with controls": 3,
        "negotiate": 4,
        "acceptable only with insurance": 5,
        "acceptable only with executive approval": 6,
        "escalate internally": 7,
        "reject": 8,
    }
    return order.get(value, 3)


def _choose_stronger_posture(current: str, candidate: str) -> str:
    return candidate if _posture_rank(candidate) > _posture_rank(current) else current


def _posture_next_step(posture: str) -> str:
    return {
        "acceptable": "Proceed only after normal commercial checks and documented business ownership.",
        "acceptable with controls": "Proceed only with the controls, amendments, or owner acknowledgements recorded.",
        "acceptable below threshold": "Keep evidence on file and confirm the value, dependency, and scope stay below internal thresholds.",
        "acceptable only with insurance": "Confirm suitable insurance coverage before approval or signature.",
        "acceptable only with executive approval": "Obtain executive approval before acceptance or signature.",
        "negotiate": "Use the highest-evidence findings as negotiation priorities before acceptance.",
        "escalate internally": "Escalate to the appropriate internal owner before the contract moves forward.",
        "reject": "Do not proceed on the current terms unless the relevant risk is removed or formally re-approved.",
        "monitor only": "No material covered signal was elevated; keep the review record and continue normal business checks.",
    }.get(posture, "Record the decision rationale before the contract moves forward.")


def build_operational_decision_posture(
    payload: dict[str, Any],
    *,
    policy_trace: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    context = _context_from_payload(payload)
    severity = str(payload.get("severity") or "LOW").upper()
    normalized_score = int(meta.get("normalized_score") or payload.get("risk_score") or 0)
    high_count = sum(1 for finding in findings if int(finding.get("severity") or 0) >= 4)
    compound = [
        finding for finding in findings
        if str(finding.get("matched_pattern") or "").startswith("derived_")
        or "cross_clause" in (finding.get("tags") or [])
        or str(finding.get("rule_id") or "").startswith("cross_")
    ]
    role = str(context.get("user_role") or "unknown")
    criticality = str(context.get("criticality_level") or "unknown")
    posture_pref = str(context.get("risk_posture") or "unknown")
    insurance = str(context.get("insurance_coverage") or "unknown")
    deal_value = _parse_money(context.get("deal_value"))
    policy_summary = meta.get("policy_status_summary") if isinstance(meta.get("policy_status_summary"), dict) else {}
    policy_trace = policy_trace or meta.get("policy_trace") or []

    posture = "monitor only" if not findings else "acceptable with controls"
    rationale: list[str] = []
    escalation_reason = None

    if not findings:
        rationale.append("No covered deterministic finding was elevated in the reviewed text.")
    elif severity == "LOW" and normalized_score < 20 and high_count == 0 and not compound:
        posture = "acceptable"
        rationale.append("Detected findings are low severity and no compound interaction was elevated.")
    elif severity == "MEDIUM" or high_count or compound:
        posture = "negotiate"
        rationale.append("Deterministic findings indicate negotiable commercial exposure.")
    if severity == "HIGH" or normalized_score >= 65 or high_count >= 2:
        posture = _choose_stronger_posture(posture, "escalate internally")
        escalation_reason = "High severity or multiple material deterministic findings."
        rationale.append("High-severity deterministic findings increase the need for internal review.")

    if criticality == "mission_critical":
        posture = _choose_stronger_posture(posture, "escalate internally")
        escalation_reason = escalation_reason or "Mission-critical context increases operational consequence."
        rationale.append("Mission-critical context increases operational exposure.")
    elif criticality == "low" and posture in {"acceptable", "acceptable with controls"}:
        posture = "acceptable below threshold"
        rationale.append("Low criticality supports a below-threshold posture where evidence remains documented.")

    if posture_pref == "conservative" and posture in {"acceptable", "acceptable with controls", "negotiate"}:
        posture = _choose_stronger_posture(posture, "negotiate" if posture.startswith("acceptable") else "escalate internally")
        rationale.append("Conservative risk posture increases review attention.")

    if role in {"seller", "supplier", "licensor", "contractor", "consultant", "agency"} and any(
        _finding_has_any(finding, {"indemn", "liability", "set-off", "liquidated damages"}) for finding in findings
    ):
        rationale.append("Provider-side context increases focus on downside exposure, margin, and insurability.")
    if role in {"buyer", "customer", "licensee", "tenant", "borrower"} and any(
        _finding_has_any(finding, {"suspension", "renewal", "termination", "data", "payment"}) for finding in findings
    ):
        rationale.append("Recipient-side context increases focus on continuity, exit, and counterparty leverage.")

    if insurance in {"not_confirmed", "insufficient", "unknown"} and any(
        _finding_has_any(finding, {"liability", "indemnity", "uncapped", "cap"}) and int(finding.get("severity") or 0) >= 4
        for finding in findings
    ):
        posture = _choose_stronger_posture(posture, "acceptable only with insurance")
        rationale.append("High liability or indemnity exposure should be checked against insurance coverage.")

    if deal_value is not None and deal_value >= 250_000 and posture in {"negotiate", "acceptable with controls", "acceptable below threshold", "acceptable"}:
        posture = _choose_stronger_posture(posture, "acceptable only with executive approval")
        rationale.append("Deal value is above the default executive-review threshold.")

    if policy_summary.get("exceeds_tolerance"):
        posture = _choose_stronger_posture(posture, "escalate internally")
        escalation_reason = escalation_reason or "One or more findings exceed configured tolerance."
        rationale.append("Configured organisation tolerance is exceeded.")
    elif policy_summary.get("conflicts_with_policy"):
        posture = _choose_stronger_posture(posture, "negotiate")
        rationale.append("One or more findings conflict with configured organisation policy.")

    policy_actions = {str(item.get("action") or "") for item in policy_trace if isinstance(item, dict)}
    if "reject" in policy_actions:
        posture = "reject"
        escalation_reason = "Organisation policy marks at least one exposure as reject."
        rationale.append("Organisation policy requires rejection unless terms change.")
    if "mandatory_legal_review" in policy_actions:
        posture = _choose_stronger_posture(posture, "escalate internally")
        escalation_reason = escalation_reason or "Organisation policy requires legal review."
        rationale.append("Organisation policy requires mandatory legal review.")
    if "executive_approval" in policy_actions:
        posture = _choose_stronger_posture(posture, "acceptable only with executive approval")
        rationale.append("Organisation policy requires executive approval.")
    if "insurance_required" in policy_actions:
        posture = _choose_stronger_posture(posture, "acceptable only with insurance")
        rationale.append("Organisation policy requires insurance confirmation.")

    if not rationale:
        rationale.append("Safe baseline posture applied from deterministic score, findings, and available context.")

    return {
        "decision_posture": posture,
        "decision_posture_code": posture,
        "posture_rationale": list(dict.fromkeys(rationale)),
        "recommended_next_step": _posture_next_step(posture),
        "escalation_reason": escalation_reason,
        "decision_posture_evidence": _evidence_refs(findings),
        "decision_posture_boundary": "Decision posture is deterministic commercial decision-support only and is not legal advice.",
    }


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


def _org_tolerance_trace(payload: dict[str, Any], policy: dict[str, str]) -> list[dict[str, Any]]:
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    context = _context_from_payload(payload)
    jurisdiction = str(context.get("jurisdiction") or "").lower()
    data_sensitivity = str(context.get("data_sensitivity") or "unknown")
    insurance = str(context.get("insurance_coverage") or "unknown")
    deal_value = _parse_money(context.get("deal_value"))
    trace: list[dict[str, Any]] = []

    has_uncapped_indemnity = any(
        _finding_has_any(finding, {"uncapped indemnity", "not subject to the liability cap", "indemnity obligations outside the cap"})
        or str(finding.get("rule_id") or "") in {"cross_low_cap_broad_indemnity", "cross_indemnity_cap_gap"}
        for finding in findings
    )
    if has_uncapped_indemnity and policy.get("uncapped_indemnity") in {"reject", "escalate", "negotiate"}:
        value = policy.get("uncapped_indemnity")
        trace.append(
            {
                "policy_key": "uncapped_indemnity",
                "policy_value": value,
                "status": "exceeds_tolerance" if value in {"reject", "escalate"} else "conflicts_with_policy",
                "action": "reject" if value == "reject" else "mandatory_legal_review",
                "reason": "Uncapped or cap-weakened indemnity detected against organisation tolerance.",
            }
        )

    if deal_value is not None:
        threshold_policy = policy.get("deal_value_threshold")
        if threshold_policy == "legal_review_over_250k" and deal_value >= 250_000:
            trace.append(
                {
                    "policy_key": "deal_value_threshold",
                    "policy_value": threshold_policy,
                    "status": "mandatory_review",
                    "action": "mandatory_legal_review",
                    "reason": "Deal value is at or above the configured legal review threshold.",
                }
            )
        elif threshold_policy == "executive_approval_over_250k" and deal_value >= 250_000:
            trace.append(
                {
                    "policy_key": "deal_value_threshold",
                    "policy_value": threshold_policy,
                    "status": "mandatory_approval",
                    "action": "executive_approval",
                    "reason": "Deal value is at or above the configured executive approval threshold.",
                }
            )
        elif threshold_policy == "legal_review_over_100k" and deal_value >= 100_000:
            trace.append(
                {
                    "policy_key": "deal_value_threshold",
                    "policy_value": threshold_policy,
                    "status": "mandatory_review",
                    "action": "mandatory_legal_review",
                    "reason": "Deal value is at or above the configured legal review threshold.",
                }
            )

    renewal_policy = policy.get("auto_renewal_duration")
    if renewal_policy in {"prohibit_over_12_months", "review_over_12_months"}:
        long_renewal = any(
            str(finding.get("rule_id") or "") in {"renewal_long_commitment", "auto_renewal_notice_trap", "cross_renewal_price_lock_in"}
            or _finding_has_any(finding, {"24 months", "two year", "successive one year", "successive 12 month"})
            for finding in findings
        )
        if long_renewal:
            trace.append(
                {
                    "policy_key": "auto_renewal_duration",
                    "policy_value": renewal_policy,
                    "status": "exceeds_tolerance" if renewal_policy == "prohibit_over_12_months" else "mandatory_review",
                    "action": "reject" if renewal_policy == "prohibit_over_12_months" else "mandatory_legal_review",
                    "reason": "Auto-renewal duration appears to exceed the configured renewal tolerance.",
                }
            )

    if policy.get("eu_data_processing") in {"require_dpa", "review"} and (
        jurisdiction in {"eu", "eea", "uk"} or data_sensitivity in {"high", "special_category"}
    ):
        has_data_findings = any(finding_policy_category(finding) == "data_use" for finding in findings)
        if has_data_findings:
            trace.append(
                {
                    "policy_key": "eu_data_processing",
                    "policy_value": policy.get("eu_data_processing"),
                    "status": "mandatory_review",
                    "action": "mandatory_legal_review",
                    "reason": "Data-related findings require DPA or data protection review under configured policy.",
                }
            )

    if policy.get("cross_border_transfer") in {"executive_approval", "review"}:
        has_transfer = any(
            str(finding.get("rule_id") or "") == "data_transfer_anonymisation_processing"
            or _finding_has_any(finding, {"cross-border", "onward transfer", "transfer"})
            for finding in findings
        )
        if has_transfer:
            trace.append(
                {
                    "policy_key": "cross_border_transfer",
                    "policy_value": policy.get("cross_border_transfer"),
                    "status": "mandatory_approval" if policy.get("cross_border_transfer") == "executive_approval" else "mandatory_review",
                    "action": "executive_approval" if policy.get("cross_border_transfer") == "executive_approval" else "mandatory_legal_review",
                    "reason": "Cross-border or onward data transfer signal triggered configured approval policy.",
                }
            )

    if policy.get("high_liability_exposure") in {"insurance_required", "escalate"}:
        high_liability = any(
            _finding_has_any(finding, {"liability", "indemnity", "uncapped", "cap"})
            and int(finding.get("severity") or 0) >= 4
            for finding in findings
        )
        if high_liability:
            trace.append(
                {
                    "policy_key": "high_liability_exposure",
                    "policy_value": policy.get("high_liability_exposure"),
                    "status": "mandatory_review",
                    "action": "insurance_required" if policy.get("high_liability_exposure") == "insurance_required" and insurance != "confirmed" else "mandatory_legal_review",
                    "reason": "High liability exposure triggered configured insurance or escalation policy.",
                }
            )

    return trace


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


def _finding_evidence(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "rule_id": finding.get("rule_id"),
        "title": finding.get("title"),
        "evidence_excerpt": finding.get("matched_text") or finding.get("excerpt"),
    }


def _families_from_payload(payload: dict[str, Any]) -> set[str]:
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    families = {str(item).lower() for item in meta.get("rule_families_detected", []) if item}
    for finding in payload.get("findings", []) or []:
        if not isinstance(finding, dict):
            continue
        category = str(finding.get("category") or "").lower()
        rule_id = str(finding.get("rule_id") or "").lower()
        title = str(finding.get("title") or "").lower()
        text = f"{category} {rule_id} {title}"
        if "indemn" in text:
            families.add("indemnity")
        if "liability" in text:
            families.add("liability")
        if "renewal" in text or "auto_renew" in text:
            families.add("auto-renewal")
        if "jurisdiction" in text or "forum" in text or "venue" in text:
            families.add("jurisdiction")
        if "data" in text:
            families.add("data use")
        if "termination" in text:
            families.add("termination")
        if "payment" in text or "fee" in text or "price" in text:
            families.add("payment")
        if "suspension" in text or "suspend" in text or category == "service":
            families.add("operational dependency")
    return families


def build_negotiation_intelligence(payload: dict[str, Any]) -> dict[str, Any]:
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    context = _context_from_payload(payload)
    posture = str(payload.get("decision_posture") or "monitor only")
    priorities: list[dict[str, Any]] = []
    minimum_controls: list[str] = []
    fallback_positions: list[str] = []
    safer_structures: list[str] = []
    leverage_indicators: list[str] = []

    for finding in findings:
        guidance = decision_guidance_for_finding(finding)
        severity = int(finding.get("severity") or 0)
        if not guidance or severity < 3:
            continue
        text = _finding_text(finding)
        objectives: list[str] = []
        if "liability" in text or "cap" in text:
            objectives.extend(["Ask for a mutual liability cap.", "Confirm insurance alignment before acceptance."])
            fallback_positions.append("If a full cap is resisted, seek a narrower uncapped carve-out and documented approval.")
            minimum_controls.append("Liability exposure must be reviewed against insurance and approval thresholds.")
        if "indemn" in text:
            objectives.append("Narrow indemnity to direct third-party claims and proportionate losses.")
            fallback_positions.append("If indemnity cannot be removed, require mutuality, exclusions, and a clear cap.")
        if "suspension" in text or "suspend" in text:
            objectives.append("Require notice and cure before suspension except for urgent security or legal-risk events.")
            minimum_controls.append("Suspension should include notice, cure period, and continuity controls where practical.")
        if "renewal" in text:
            objectives.append("Reduce auto-renewal friction and require usable non-renewal notice.")
            safer_structures.append("Use renewal notice windows that give the business practical time to exit or renegotiate.")
        if "data" in text or "ai training" in text:
            objectives.append("Require a DPA or equivalent data-use controls where personal or sensitive data is involved.")
            safer_structures.append("Separate service-use data rights from analytics, training, onward sharing, and transfers.")
        if "jurisdiction" in text or "forum" in text:
            objectives.append("Confirm forum, law, and escalation route are commercially workable.")
        if "refund" in text or "prepaid" in text:
            objectives.append("Add refund, credit, or service-continuity protection for prepaid amounts.")

        if objectives:
            priorities.append(
                {
                    "rule_id": finding.get("rule_id"),
                    "title": finding.get("title"),
                    "priority": "high" if severity >= 4 or posture in {"escalate internally", "reject"} else "medium",
                    "clause_revision_objectives": sorted(dict.fromkeys(objectives)),
                    "evidence": _finding_evidence(finding),
                }
            )

    leverage = str(context.get("negotiation_leverage") or "unknown")
    if leverage in {"low", "limited"}:
        leverage_indicators.append("Negotiation leverage appears limited; focus on minimum controls and approval record.")
    elif leverage in {"high", "strong"}:
        leverage_indicators.append("Negotiation leverage appears stronger; prioritize structural fixes before fallback positions.")
    if str(context.get("risk_posture") or "") == "conservative":
        minimum_controls.append("Conservative posture supports stronger escalation before accepting unresolved high-risk wording.")
    if not priorities:
        return {
            "priorities": [],
            "fallback_positions": [],
            "safer_alternative_structures": [],
            "leverage_indicators": leverage_indicators,
            "minimum_acceptable_controls": [],
            "boundary": "Negotiation intelligence is preparation support only and is not legal drafting advice.",
        }
    return {
        "priorities": priorities[:8],
        "fallback_positions": sorted(dict.fromkeys(fallback_positions))[:8],
        "safer_alternative_structures": sorted(dict.fromkeys(safer_structures))[:8],
        "leverage_indicators": leverage_indicators,
        "minimum_acceptable_controls": sorted(dict.fromkeys(minimum_controls))[:8],
        "boundary": "Negotiation intelligence is preparation support only and is not legal drafting advice.",
    }


def build_sector_jurisdiction_intelligence(payload: dict[str, Any]) -> dict[str, Any]:
    context = _context_from_payload(payload)
    findings = [finding for finding in payload.get("findings", []) if isinstance(finding, dict)]
    families = _families_from_payload(payload)
    industry = str(context.get("industry") or context.get("contract_type") or "").lower()
    contract_type = str(context.get("contract_type") or "").lower()
    jurisdiction = str(context.get("jurisdiction") or "").lower()
    data_sensitivity = str(context.get("data_sensitivity") or "").lower()
    notes: list[dict[str, Any]] = []

    if (industry in {"saas", "ai_vendors"} or contract_type == "saas") and ("data use" in families or data_sensitivity in {"high", "special_category"}):
        notes.append(
            {
                "type": "sector",
                "signal": "SaaS/data-sensitive review attention",
                "note": "Data-use, training, transfer, confidentiality, and service-continuity terms deserve focused operational review.",
            }
        )
    if industry in {"healthcare", "fintech"} and ("data use" in families or data_sensitivity in {"high", "special_category"}):
        notes.append(
            {
                "type": "sector",
                "signal": f"{industry} data/compliance attention",
                "note": "Sensitive or regulated operating context increases the need to check data, confidentiality, audit, and operational controls.",
            }
        )
    if industry == "real_estate" or contract_type == "lease":
        notes.append(
            {
                "type": "sector",
                "signal": "Real-estate/lease relevance",
                "note": "Lease, payment, exit, repair, liability, and possession-related terms should be interpreted against the property use case.",
            }
        )

    jurisdiction_findings = [
        finding for finding in findings
        if str(finding.get("category") or "").lower() == "jurisdiction"
        or "jurisdiction" in str(finding.get("rule_id") or "").lower()
        or "venue" in str(finding.get("rule_id") or "").lower()
    ]
    if jurisdiction_findings:
        locations = {
            str(finding.get("matched_location") or "").strip().lower()
            for finding in jurisdiction_findings
            if finding.get("matched_location")
        }
        if jurisdiction and locations and jurisdiction not in locations:
            notes.append(
                {
                    "type": "jurisdiction",
                    "signal": "Potential forum burden",
                    "note": "Detected forum or venue wording may differ from the supplied jurisdiction context; treat this as an operational legal-review signal, not a legal opinion.",
                    "evidence": [_finding_evidence(finding) for finding in jurisdiction_findings[:3]],
                }
            )
        elif jurisdiction:
            notes.append(
                {
                    "type": "jurisdiction",
                    "signal": "Jurisdiction review signal",
                    "note": "Jurisdiction or forum wording was detected and should be checked for enforceability, cost, and operational practicality.",
                    "evidence": [_finding_evidence(finding) for finding in jurisdiction_findings[:3]],
                }
            )

    return {
        "sector": industry or contract_type or "unknown",
        "jurisdiction": jurisdiction or None,
        "notes": notes,
        "available_sector_pack": SECTOR_INTELLIGENCE_PACKS.get(industry) or SECTOR_INTELLIGENCE_PACKS.get(contract_type),
        "boundary": "Industry and jurisdiction signals are operational risk indicators, not legal opinions.",
    }


def apply_memory_and_linked_intelligence(
    payload: dict[str, Any],
    *,
    memory_signals: dict[str, Any] | None = None,
    linked_document_signals: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = payload.setdefault("meta", {})
    if memory_signals is not None:
        meta["contract_memory"] = memory_signals
    if linked_document_signals is not None:
        meta["linked_document_intelligence"] = linked_document_signals
    snapshot = meta.get("decision_intelligence")
    if isinstance(snapshot, dict):
        if memory_signals is not None:
            snapshot["contract_memory"] = memory_signals
        if linked_document_signals is not None:
            snapshot["linked_document_intelligence"] = linked_document_signals
            snapshot["linked_document_context"] = linked_document_signals.get("linked_document_context")
        snapshot["negotiation_intelligence"] = meta.get("negotiation_intelligence")
        snapshot["sector_jurisdiction_intelligence"] = meta.get("sector_jurisdiction_intelligence")
    return payload


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
    policy_trace = _org_tolerance_trace(payload, normalized_policy)
    if policy_trace:
        meta["policy_trace"] = policy_trace
        for item in policy_trace:
            status = str(item.get("status") or "")
            if status in {"exceeds_tolerance", "mandatory_review", "mandatory_approval", "conflicts_with_policy"}:
                policy_counts[status] += 1
            key = str(item.get("policy_key") or "")
            if status in {"exceeds_tolerance", "mandatory_review", "mandatory_approval", "conflicts_with_policy"} and key:
                breaches[key] += 1
    meta["policy_status_summary"] = dict(policy_counts)
    meta["most_common_policy_breaches"] = [
        {"policy_category": key, "count": count} for key, count in breaches.most_common()
    ]
    posture = build_operational_decision_posture(payload, policy_trace=policy_trace)
    payload.update(posture)
    meta["decision_posture"] = posture["decision_posture"]
    meta["posture_rationale"] = posture["posture_rationale"]
    meta["recommended_next_step"] = posture["recommended_next_step"]
    meta["escalation_reason"] = posture["escalation_reason"]
    meta["negotiation_intelligence"] = build_negotiation_intelligence(payload)
    meta["sector_jurisdiction_intelligence"] = build_sector_jurisdiction_intelligence(payload)
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
    posture = payload.get("decision_posture") or "monitor only"
    posture_rationale = payload.get("posture_rationale") or []
    recommended_next_step = payload.get("recommended_next_step")
    escalation_reason = payload.get("escalation_reason")
    posture_summary = "Decision posture is pending; deterministic scoring remains the governing core."
    if prior_outcome_hint and prior_outcome_hint.get("state") and prior_outcome_hint.get("family"):
        posture_summary = (
            f"Your organisation {prior_outcome_hint['state']} this type of risk in prior contracts; "
            "this scan follows the same pattern unless a commercial exception is recorded."
        )
    elif policy_summary.get("exceeds_tolerance"):
        posture_summary = "One or more findings exceed configured tolerance and should be escalated or documented before acceptance."
    elif policy_summary.get("conflicts_with_policy"):
        posture_summary = "One or more findings conflict with usual policy and should be negotiated or exception-tracked."
    elif policy_summary.get("policy_unknown"):
        posture_summary = "Policy unknown for one or more findings; decision posture is conservative until tolerance is configured."

    return {
        "decision_posture": posture_summary,
        "decision_posture_code": posture,
        "decision_posture_summary": posture_summary,
        "posture_rationale": posture_rationale,
        "recommended_next_step": recommended_next_step,
        "escalation_reason": escalation_reason,
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
        "negotiation_intelligence": payload.get("meta", {}).get("negotiation_intelligence"),
        "sector_jurisdiction_intelligence": payload.get("meta", {}).get("sector_jurisdiction_intelligence"),
        "policy_status_summary": policy_summary,
        "metadata": INTELLIGENCE_METADATA,
        "boundary_notice": "Decision intelligence, negotiation preparation, industry/jurisdiction signals, memory, and linked-document checks support management review only. They are not legal advice, legal drafting, complete due diligence, or legal-outcome engines.",
    }


def context_bucket_from_scan(scan_context: dict[str, Any] | None, key: str) -> str:
    if not scan_context:
        return "unknown"
    context = scan_context.get("context") if isinstance(scan_context.get("context"), dict) else scan_context
    return str((context or {}).get(key) or "unknown")


def today_iso() -> str:
    return date.today().isoformat()
