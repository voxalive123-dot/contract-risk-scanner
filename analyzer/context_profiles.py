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


def build_context_profile_metadata(
    *,
    jurisdiction: Optional[str] = None,
    sector: Optional[str] = None,
    contract_type: Optional[str] = None,
    user_role: Optional[str] = None,
    objective: Optional[str] = None,
) -> Dict[str, Any]:
    jurisdiction_key = _normalize_key(jurisdiction)
    sector_key = _normalize_key(sector)

    profile = {
        "version": CONTEXT_PROFILE_VERSION,
        "jurisdiction": jurisdiction_key if jurisdiction_key in JURISDICTION_PROFILES else None,
        "sector": sector_key if sector_key in SECTOR_PROFILES else None,
        "risk_positioning": "contextual warning support only; no legal outcome prediction",
        "playbook_placeholders": deepcopy(PLAYBOOK_PLACEHOLDERS),
        "localization_ready": True,
        "benchmark_context": benchmark_context,
        "audit": deepcopy(CONTEXT_PROFILE_AUDIT),
    }
    profile["playbook_placeholders"].update(
        {
            "contract_type": contract_type,
            "user_role": user_role,
            "objective": objective,
        }
    )
    return profile
