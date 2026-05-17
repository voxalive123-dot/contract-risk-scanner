from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


CONTEXT_PROFILE_VERSION = "0.2.0"
CONTEXT_PROFILE_LAST_UPDATED = "2026-05-17"


JURISDICTION_PROFILES: Dict[str, Dict[str, Any]] = {
    "uk": {
        "label": "UK",
        "purpose": "Adjust warning and disclaimer wording without predicting legal outcomes.",
        "disclaimer": "Clause risk can vary under UK law and should be reviewed in its commercial and legal context.",
        "future_sensitivity": ["consumer terms", "data protection", "liability limits"],
    },
    "us": {
        "label": "US",
        "purpose": "Adjust warning and disclaimer wording without predicting legal outcomes.",
        "disclaimer": "Clause risk can vary by US state and forum; this review does not assume uniform legal effect.",
        "future_sensitivity": ["state law variation", "class action terms", "indemnity scope"],
    },
    "eu": {
        "label": "EU",
        "purpose": "Adjust warning and disclaimer wording without predicting legal outcomes.",
        "disclaimer": "Clause risk can vary across EU member states and regulatory contexts.",
        "future_sensitivity": ["GDPR", "cross-border data transfers", "consumer and platform rules"],
    },
}


SECTOR_PROFILES: Dict[str, Dict[str, Any]] = {
    "saas": {
        "label": "SaaS",
        "purpose": "Support context-aware emphasis for subscription, service continuity, data, and exit risks.",
        "emphasis": ["renewal", "service continuity", "data portability", "payment leverage"],
    },
    "supplier_services": {
        "label": "supplier services",
        "purpose": "Support context-aware emphasis for delivery control, remedies, subcontracting, and exit risks.",
        "emphasis": ["scope control", "remedies", "subcontracting", "termination"],
    },
    "healthcare": {
        "label": "healthcare",
        "purpose": "Support context-aware emphasis for sensitive data, operational continuity, and compliance governance.",
        "emphasis": ["sensitive data", "continuity", "audit", "regulatory governance"],
    },
    "logistics": {
        "label": "logistics",
        "purpose": "Support context-aware emphasis for delay, service levels, liability, and continuity risks.",
        "emphasis": ["delay", "service levels", "liability", "force majeure"],
    },
    "recruitment": {
        "label": "recruitment",
        "purpose": "Support context-aware emphasis for fees, replacement remedies, confidentiality, and restrictive terms.",
        "emphasis": ["fees", "replacement remedies", "confidentiality", "restraints"],
    },
    "data_heavy_contracts": {
        "label": "data-heavy contracts",
        "purpose": "Support context-aware emphasis for data use, disclosure, transfer, retention, and confidentiality.",
        "emphasis": ["data use", "onward transfer", "retention", "confidentiality"],
    },
    "procurement": {
        "label": "procurement",
        "purpose": "Support context-aware emphasis for price variation, payment, delivery, remedies, and audit controls.",
        "emphasis": ["price variation", "payment", "delivery", "audit"],
    },
}


USER_ROLE_VALUES = {
    "buyer",
    "seller",
    "supplier",
    "customer",
    "landlord",
    "tenant",
    "lender",
    "borrower",
    "partner",
    "licensor",
    "licensee",
    "employer",
    "employee",
    "other",
    # Legacy values retained for backward compatibility.
    "saas_provider",
    "agency",
    "consultant",
    "contractor",
    "reseller",
    "processor",
    "controller",
    "unknown",
}

CONTRACT_TYPE_VALUES = {
    "saas",
    "supplier_agreement",
    "nda",
    "lease",
    "employment",
    "reseller",
    "partnership",
    "loan",
    "procurement",
    "data_processing",
    "franchise",
    "services",
    "government",
    "other",
    # Legacy values retained for backward compatibility.
    "consultancy",
    "logistics",
    "security_services",
    "healthcare",
    "unknown",
}

COUNTERPARTY_PROFILE_VALUES = {
    "larger_counterparty",
    "smaller_counterparty",
    "strategic_customer",
    "key_supplier",
    "public_sector",
    "regulated_party",
    "unknown",
}

VALUE_CRITICALITY_VALUES = {
    "low_value",
    "high_value",
    "business_critical",
    "recurring",
    "one_off",
    "pilot",
    "strategic_partnership",
    "unknown",
}

CRITICALITY_LEVEL_VALUES = {
    "low",
    "medium",
    "high",
    "mission_critical",
    "unknown",
}

RISK_POSTURE_VALUES = {
    "balanced",
    "conservative",
    "aggressive_growth",
    "unknown",
}

NEGOTIATION_LEVERAGE_VALUES = {
    "low",
    "medium",
    "high",
    "unknown",
}

COUNTERPARTY_TIER_VALUES = {
    "startup",
    "sme",
    "mid_market",
    "enterprise",
    "public_sector",
    "strategic",
    "unknown",
}

DATA_SENSITIVITY_VALUES = {
    "none",
    "low",
    "moderate",
    "high",
    "special_category",
    "unknown",
}

INSURANCE_COVERAGE_VALUES = {
    "unknown",
    "not_applicable",
    "not_confirmed",
    "confirmed",
    "insufficient",
}

DOCUMENT_POSITION_VALUES = {
    "vendor_paper",
    "negotiated_draft",
    "renewal",
    "amendment",
    "supplier_terms",
    "customer_terms",
    "unknown",
}

MISSING_CONTEXT_MESSAGE = "Context not provided; decision posture is conservative."


RISK_APPETITE_SETTINGS: Dict[str, Dict[str, Any]] = {
    "conservative": {
        "label": "conservative",
        "purpose": "Lightly increase emphasis for stacked or high-severity findings.",
        "constraints": ["never hide findings", "never remove evidence", "never corrupt core score"],
    },
    "balanced": {
        "label": "balanced",
        "purpose": "Default review posture preserving core scoring and evidence.",
        "constraints": ["never hide findings", "never remove evidence", "never corrupt core score"],
    },
    "aggressive": {
        "label": "aggressive",
        "purpose": "Lightly reduce emphasis where supported by existing compatible metadata only.",
        "constraints": ["never hide findings", "never remove evidence", "never corrupt core score"],
    },
}


PLAYBOOK_PLACEHOLDERS: Dict[str, Optional[str]] = {
    "contract_type": None,
    "user_role": None,
    "criticality_level": None,
    "risk_posture": None,
    "counterparty_profile": None,
    "value_criticality": None,
    "document_position": None,
    "deal_value": None,
    "industry": None,
    "jurisdiction": None,
    "negotiation_leverage": None,
    "counterparty_tier": None,
    "data_sensitivity": None,
    "insurance_coverage": None,
    "objective": None,
}


LOCALIZATION_READINESS: Dict[str, Any] = {
    "spelling_normalization_hooks": {
        "uk_to_us": {"analyse": "analyze", "authorise": "authorize", "licence": "license"},
        "us_to_uk": {"analyze": "analyse", "authorize": "authorise", "license": "licence"},
    },
    "multilingual_review_placeholder": None,
    "full_translation_enabled": False,
}


benchmark_context = None


SYNTHESIS_PATTERN_METADATA: Dict[str, Dict[str, str]] = {
    "low_cap_broad_indemnity": {
        "version": "0.1.0",
        "last_updated": CONTEXT_PROFILE_LAST_UPDATED,
        "change_note": "Detect liability-cap protection weakened by broad indemnity or carve-outs.",
    },
    "termination_no_refund": {
        "version": "0.1.0",
        "last_updated": CONTEXT_PROFILE_LAST_UPDATED,
        "change_note": "Detect termination rights paired with retained prepaid or non-refundable fees.",
    },
    "data_confidentiality_gap": {
        "version": "0.1.0",
        "last_updated": CONTEXT_PROFILE_LAST_UPDATED,
        "change_note": "Detect broad data rights paired with weak confidentiality controls.",
    },
    "upfront_payment_suspension": {
        "version": "0.1.0",
        "last_updated": CONTEXT_PROFILE_LAST_UPDATED,
        "change_note": "Detect early payment exposure paired with broad supplier suspension rights.",
    },
}


CONTEXT_PROFILE_AUDIT: Dict[str, str] = {
    "version": CONTEXT_PROFILE_VERSION,
    "last_updated": CONTEXT_PROFILE_LAST_UPDATED,
    "change_note": "Adds first-class context intelligence capture while preserving deterministic rule authority.",
}


def _normalize_key(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return value.strip().lower().replace("-", "_").replace(" ", "_") or None


def normalize_context_value(value: Optional[str], allowed_values: set[str]) -> str:
    key = _normalize_key(value)
    if key in allowed_values:
        return key
    return "unknown"


def context_confidence_for(values: Dict[str, str]) -> str:
    required_keys = ("user_role", "contract_type", "criticality_level", "risk_posture")
    required_provided = sum(1 for key in required_keys if values.get(key) != "unknown")
    optional_provided = sum(
        1
        for key, value in values.items()
        if key not in required_keys and value not in {None, "", "unknown"}
    )
    if required_provided == len(required_keys):
        return "high"
    if required_provided >= 2 or optional_provided >= 2:
        return "medium"
    return "low"


def context_emphasis_notes(values: Dict[str, str]) -> list[str]:
    notes: list[str] = []
    role = values.get("user_role", "unknown")
    contract_type = values.get("contract_type", "unknown")
    criticality = values.get("criticality_level", "unknown")
    legacy_criticality = values.get("value_criticality", "unknown")
    risk_posture = values.get("risk_posture", "unknown")
    data_sensitivity = values.get("data_sensitivity", "unknown")

    if role in {"buyer", "customer", "tenant", "borrower", "licensee", "employee"}:
        notes.append("Recipient-side posture: emphasize operational continuity, payment leverage, supplier control, and exit exposure.")
    elif role in {"seller", "supplier", "landlord", "lender", "licensor", "employer", "saas_provider", "consultant", "agency"}:
        notes.append("Provider-side posture: emphasize downside exposure, obligation scope, margin protection, and insurability.")

    if contract_type in {"saas", "data_processing", "healthcare"} or data_sensitivity in {"high", "special_category"}:
        notes.append("Data-sensitive posture: emphasize governance, confidentiality, trust, and transfer controls.")

    if criticality in {"high", "mission_critical"} or legacy_criticality in {"high_value", "business_critical", "strategic_partnership"}:
        notes.append("Criticality posture: escalation language should be stronger where evidence supports material exposure.")
    elif criticality == "low" or legacy_criticality in {"low_value", "one_off", "pilot"}:
        notes.append("Limited-criticality posture: keep findings visible while moderating escalation language.")

    if risk_posture == "conservative":
        notes.append("Conservative posture: prioritize review and escalation of control, liability, renewal, and continuity risks.")
    elif risk_posture == "aggressive_growth":
        notes.append("Growth posture: preserve risk visibility while distinguishing blocker issues from managed commercial trade-offs.")

    if not notes:
        notes.append(MISSING_CONTEXT_MESSAGE)
    return notes


def build_context_profile_metadata(
    *,
    jurisdiction: Optional[str] = None,
    sector: Optional[str] = None,
    contract_type: Optional[str] = None,
    user_role: Optional[str] = None,
    counterparty_profile: Optional[str] = None,
    value_criticality: Optional[str] = None,
    document_position: Optional[str] = None,
    criticality_level: Optional[str] = None,
    risk_posture: Optional[str] = None,
    deal_value: Optional[str] = None,
    industry: Optional[str] = None,
    negotiation_leverage: Optional[str] = None,
    counterparty_tier: Optional[str] = None,
    data_sensitivity: Optional[str] = None,
    insurance_coverage: Optional[str] = None,
    objective: Optional[str] = None,
) -> Dict[str, Any]:
    jurisdiction_key = _normalize_key(jurisdiction)
    sector_key = _normalize_key(sector)
    industry_key = _normalize_key(industry)
    normalized_criticality = normalize_context_value(criticality_level, CRITICALITY_LEVEL_VALUES)
    if normalized_criticality == "unknown":
        legacy_criticality = normalize_context_value(value_criticality, VALUE_CRITICALITY_VALUES)
        if legacy_criticality in {"high_value", "business_critical", "strategic_partnership"}:
            normalized_criticality = "high"
        elif legacy_criticality in {"low_value", "one_off", "pilot"}:
            normalized_criticality = "low"
    context_values = {
        "user_role": normalize_context_value(user_role, USER_ROLE_VALUES),
        "contract_type": normalize_context_value(contract_type, CONTRACT_TYPE_VALUES),
        "criticality_level": normalized_criticality,
        "risk_posture": normalize_context_value(risk_posture, RISK_POSTURE_VALUES),
        "counterparty_profile": normalize_context_value(counterparty_profile, COUNTERPARTY_PROFILE_VALUES),
        "value_criticality": normalize_context_value(value_criticality, VALUE_CRITICALITY_VALUES),
        "document_position": normalize_context_value(document_position, DOCUMENT_POSITION_VALUES),
        "deal_value": str(deal_value).strip()[:80] if deal_value is not None and str(deal_value).strip() else None,
        "industry": industry_key,
        "jurisdiction": jurisdiction_key,
        "negotiation_leverage": normalize_context_value(negotiation_leverage, NEGOTIATION_LEVERAGE_VALUES),
        "counterparty_tier": normalize_context_value(counterparty_tier, COUNTERPARTY_TIER_VALUES),
        "data_sensitivity": normalize_context_value(data_sensitivity, DATA_SENSITIVITY_VALUES),
        "insurance_coverage": normalize_context_value(insurance_coverage, INSURANCE_COVERAGE_VALUES),
    }
    confidence = context_confidence_for(context_values)

    profile = {
        "version": CONTEXT_PROFILE_VERSION,
        "jurisdiction": jurisdiction_key if jurisdiction_key in JURISDICTION_PROFILES else jurisdiction_key,
        "sector": sector_key if sector_key in SECTOR_PROFILES else sector_key,
        "risk_positioning": "contextual warning support only; deterministic findings remain the truth layer",
        "context": context_values,
        "context_confidence": confidence,
        "context_limitations": [] if confidence != "low" else [MISSING_CONTEXT_MESSAGE],
        "context_emphasis": context_emphasis_notes(context_values),
        "playbook_placeholders": deepcopy(PLAYBOOK_PLACEHOLDERS),
        "localization_ready": True,
        "benchmark_context": benchmark_context,
        "audit": deepcopy(CONTEXT_PROFILE_AUDIT),
    }
    profile["playbook_placeholders"].update(
        {
            "contract_type": context_values["contract_type"],
            "user_role": context_values["user_role"],
            "criticality_level": context_values["criticality_level"],
            "risk_posture": context_values["risk_posture"],
            "counterparty_profile": context_values["counterparty_profile"],
            "value_criticality": context_values["value_criticality"],
            "document_position": context_values["document_position"],
            "deal_value": context_values["deal_value"],
            "industry": context_values["industry"],
            "jurisdiction": context_values["jurisdiction"],
            "negotiation_leverage": context_values["negotiation_leverage"],
            "counterparty_tier": context_values["counterparty_tier"],
            "data_sensitivity": context_values["data_sensitivity"],
            "insurance_coverage": context_values["insurance_coverage"],
            "objective": objective,
        }
    )
    return profile
