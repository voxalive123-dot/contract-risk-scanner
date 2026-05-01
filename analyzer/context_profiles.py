from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional


CONTEXT_PROFILE_VERSION = "0.1.0"
CONTEXT_PROFILE_LAST_UPDATED = "2026-05-01"


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
    "supplier",
    "saas_provider",
    "agency",
    "consultant",
    "employer",
    "contractor",
    "reseller",
    "processor",
    "controller",
    "unknown",
}

CONTRACT_TYPE_VALUES = {
    "saas",
    "services",
    "consultancy",
    "procurement",
    "employment",
    "lease",
    "data_processing",
    "franchise",
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
    "counterparty_profile": None,
    "value_criticality": None,
    "document_position": None,
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
    "change_note": "Initial non-invasive global market intelligence readiness foundation.",
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
    provided = sum(1 for value in values.values() if value != "unknown")
    if provided >= 4:
        return "high"
    if provided >= 2:
        return "medium"
    return "low"


def context_emphasis_notes(values: Dict[str, str]) -> list[str]:
    notes: list[str] = []
    role = values.get("user_role", "unknown")
    contract_type = values.get("contract_type", "unknown")
    criticality = values.get("value_criticality", "unknown")

    if role == "buyer":
        notes.append("Buyer posture: emphasize operational continuity, cash-flow exposure, and supplier control rights.")
    elif role in {"supplier", "saas_provider", "consultant", "agency"}:
        notes.append("Supplier posture: emphasize downside exposure, margin protection, and obligation scope.")

    if contract_type in {"saas", "data_processing", "healthcare"}:
        notes.append("Data-heavy posture: emphasize governance, confidentiality, trust, and transfer controls.")

    if criticality in {"high_value", "business_critical", "strategic_partnership"}:
        notes.append("Criticality posture: escalation language should be stronger where evidence supports material exposure.")
    elif criticality in {"low_value", "one_off", "pilot"}:
        notes.append("Limited-criticality posture: keep findings visible while moderating escalation language.")

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
    objective: Optional[str] = None,
) -> Dict[str, Any]:
    jurisdiction_key = _normalize_key(jurisdiction)
    sector_key = _normalize_key(sector)
    context_values = {
        "user_role": normalize_context_value(user_role, USER_ROLE_VALUES),
        "contract_type": normalize_context_value(contract_type, CONTRACT_TYPE_VALUES),
        "counterparty_profile": normalize_context_value(counterparty_profile, COUNTERPARTY_PROFILE_VALUES),
        "value_criticality": normalize_context_value(value_criticality, VALUE_CRITICALITY_VALUES),
        "document_position": normalize_context_value(document_position, DOCUMENT_POSITION_VALUES),
    }
    confidence = context_confidence_for(context_values)

    profile = {
        "version": CONTEXT_PROFILE_VERSION,
        "jurisdiction": jurisdiction_key if jurisdiction_key in JURISDICTION_PROFILES else None,
        "sector": sector_key if sector_key in SECTOR_PROFILES else None,
        "risk_positioning": "contextual warning support only; no legal outcome prediction",
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
            "counterparty_profile": context_values["counterparty_profile"],
            "value_criticality": context_values["value_criticality"],
            "document_position": context_values["document_position"],
            "objective": objective,
        }
    )
    return profile
