"use client";

import Link from "next/link";
import { ChangeEvent, type ReactNode, useEffect, useMemo, useRef, useState } from "react";

import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

type ScoreAdjustment = {
  type?: string;
  effect?: number;
  reason?: string;
};

type RoleAwareInterpretation = Partial<{
  "Structural Risk": string;
  "Contextual Impact": string;
  "Operational Exposure": string;
  "Recommended Attention": string;
}>;

type PolicyTraceItem = {
  policy_key?: string;
  policy_value?: string;
  status?: string;
  action?: string;
  reason?: string;
};

type DecisionIntelligenceSnapshot = {
  decision_posture?: string;
  decision_posture_code?: string;
  decision_posture_summary?: string;
  posture_rationale?: string[];
  recommended_next_step?: string;
  escalation_reason?: string | null;
  policy_status_summary?: Record<string, number>;
  contract_memory?: ContractMemorySignal | null;
  linked_document_intelligence?: LinkedDocumentSignal | null;
  negotiation_intelligence?: NegotiationIntelligence | null;
  sector_jurisdiction_intelligence?: SectorJurisdictionSignal | null;
};

type DecisionPostureDisplay = {
  label: string;
  detail: string;
  nextStep: string;
  escalationReason?: string | null;
};

type ContractMemorySignal = {
  recurring_counterparty?: { detected?: boolean; counterparty_key?: string; prior_scan_count?: number };
  recurring_risky_clauses?: Array<{ family?: string; prior_count?: number }>;
  escalation_history?: Array<{ family?: string; count?: number }>;
  boundary?: string;
};

type NegotiationIntelligence = {
  priorities?: Array<{ title?: string; priority?: string; clause_revision_objectives?: string[] }>;
  fallback_positions?: string[];
  minimum_acceptable_controls?: string[];
  boundary?: string;
};

type SectorJurisdictionSignal = {
  notes?: Array<{ type?: string; signal?: string; note?: string }>;
  boundary?: string;
};

type LinkedDocumentSignal = {
  contract_set_detected?: boolean;
  related_scan_count?: number;
  conflict_signals?: Array<{ type?: string; note?: string }>;
  boundary?: string;
};

type Finding = {
  rule_id?: string;
  title?: string;
  category?: string;
  severity?: number;
  rationale?: string;
  matched_text?: string;
  excerpt?: string;
  matched_location?: string | null;
  context_note?: string | null;
  contextual_emphasis?: string | null;
  policy_category?: string | null;
  policy_value?: string | null;
  policy_status?: string | null;
  policy_explanation?: string | null;
  decision_guidance?: string[];
  role_aware_family?: string | null;
  role_aware_interpretation?: RoleAwareInterpretation | null;
  structural_risk?: string | null;
  contextual_impact?: string | null;
  operational_exposure?: string | null;
  recommended_attention?: string | null;
  matched_pattern?: string | null;
  tags?: string[];
  triggered_by?: string[];
};

type TopRisk = {
  rule_id?: string;
  title?: string;
  category?: string;
  severity?: number;
  weight?: number;
  matched_location?: string | null;
  context_note?: string | null;
};

type AnalyzeResult = {
  risk_score: number;
  severity: "LOW" | "MEDIUM" | "HIGH";
  flags: string[];
  findings?: Finding[];
  meta?: {
    normalized_score?: number;
    contradiction_count?: number;
    score_adjustments?: ScoreAdjustment[];
    top_risks?: TopRisk[];
    confidence?: number;
    matched_rule_count?: number;
    suppressed_rule_count?: number;
    ruleset_version?: string;
    word_count?: number;
    rule_families_detected?: string[];
    synthesis_patterns_triggered?: string[];
    context_profile_used?: Record<string, unknown> | null;
    context_confidence?: string | null;
    context_limitations?: string[];
    context_emphasis?: string[];
    confidence_driver?: string | null;
    signal_type?: string | null;
    primary_risk_type?: string | null;
    reliability_wording?: string | null;
    decision_posture?: string | null;
    posture_rationale?: string[];
    recommended_next_step?: string | null;
    escalation_reason?: string | null;
    policy_trace?: PolicyTraceItem[];
    decision_intelligence?: DecisionIntelligenceSnapshot | null;
    contract_memory?: ContractMemorySignal | null;
    negotiation_intelligence?: NegotiationIntelligence | null;
    sector_jurisdiction_intelligence?: SectorJurisdictionSignal | null;
    linked_document_intelligence?: LinkedDocumentSignal | null;
  };
  decision_posture?: string | null;
  decision_posture_code?: string | null;
  posture_rationale?: string[];
  recommended_next_step?: string | null;
  escalation_reason?: string | null;
  extraction_method?: string | null;
  confidence_hint?: number | null;
  source_type?: string | null;
  page_count?: number | null;
  has_extractable_text?: boolean | null;
};

type ScanHistoryItem = {
  id: string;
  created_at?: string | null;
  source_title?: string | null;
  source_type?: string | null;
  risk_score: number;
  normalized_score?: number | null;
  meta?: { normalized_score?: number | null } | null;
  severity?: "LOW" | "MEDIUM" | "HIGH" | string | null;
  confidence?: number;
  top_findings?: Finding[];
  clause_families_detected?: string[];
  synthesis_patterns_triggered?: string[];
  report_export_state?: string | null;
  context_profile_snapshot?: Record<string, unknown> | null;
  decision_state?: ScanDecisionState;
  finding_decisions?: FindingDecisionState[];
  notes?: Array<{ id: string; note: string; finding_rule_id?: string | null }>;
  decision_intelligence_snapshot?: DecisionIntelligenceSnapshot | null;
};

type ScanHistoryResponse = {
  scans?: ScanHistoryItem[];
  recurring_clause_families?: Array<{ family: string; count: number }>;
};

type AIReviewEvidenceNote = {
  rule_id?: string;
  title?: string;
  explanation?: string;
  evidence_excerpt?: string;
};

type AIReviewSummary = {
  raw_text?: string;
  executive_overview?: string;
  primary_risk_drivers?: string[];
  recommended_review_focus?: string[];
  evidence_signals?: string[];
  boundary_note?: string;
  overview?: string;
  risk_posture_summary?: string;
  negotiation_focus?: string[];
  evidence_notes?: AIReviewEvidenceNote[];
  uncertainty_notes?: string[];
  boundary_notice?: string;
};

type AIExplainResponse = AIReviewSummary & {
  status?: "available" | "disabled" | "unavailable";
  model?: string;
  source?: string;
  reason?: string;
  ai_summary?: AIReviewSummary | string;
  summary?: AIReviewSummary | string;
  ai_review?: AIReviewSummary | string;
  review_notes?: AIReviewSummary | string;
  data?: {
    ai_summary?: AIReviewSummary | string;
    summary?: AIReviewSummary | string;
  };
};

type NormalizedAIExplainResponse = Omit<AIExplainResponse, "ai_summary"> & {
  status: "available";
  ai_summary: AIReviewSummary;
};

type AIReviewDisplaySection = {
  heading: string;
  items: string[];
  kind: "paragraph" | "bullets" | "boundary";
};

type DashboardAccountContext = {
  user: { email: string };
  organization: { id: string; name: string };
  membership: { role: string; status: string };
  entitlement: {
    source: string;
    effective_plan: string;
    subscription_state: string;
    monthly_scan_limit: number;
    paid_access: boolean;
    ai_review_notes_allowed: boolean;
    reason: string;
  };
};

type AuthState = "loading" | "authenticated" | "unauthenticated";

type ScanDecisionValue =
  | "pending"
  | "accepted"
  | "negotiated"
  | "escalated"
  | "rejected"
  | "sent_for_legal_review";

type FindingDecisionValue = "unresolved" | "accepted" | "redlined" | "waived" | "escalated" | "ignored";

type ScanDecisionState = {
  state?: ScanDecisionValue | string | null;
  reason_code?: string | null;
  note?: string | null;
  updated_at?: string | null;
};

type FindingDecisionState = {
  finding_id?: string | null;
  status?: FindingDecisionValue | string | null;
  reason_code?: string | null;
  note?: string | null;
  updated_at?: string | null;
};

const SCAN_DECISION_OPTIONS: Array<{ value: ScanDecisionValue; label: string }> = [
  { value: "pending", label: "Pending" },
  { value: "accepted", label: "Accepted" },
  { value: "negotiated", label: "Negotiated" },
  { value: "escalated", label: "Escalated" },
  { value: "rejected", label: "Rejected" },
  { value: "sent_for_legal_review", label: "Sent for legal review" },
];

const FINDING_DECISION_OPTIONS: Array<{ value: FindingDecisionValue; label: string }> = [
  { value: "unresolved", label: "Unresolved" },
  { value: "accepted", label: "Accepted" },
  { value: "redlined", label: "Redlined" },
  { value: "waived", label: "Waived" },
  { value: "escalated", label: "Escalated" },
  { value: "ignored", label: "Ignored" },
];

const DOCUMENT_TYPE_OPTIONS = [
  { label: "Supplier Agreement", value: "supplier_agreement" },
  { label: "NDA", value: "nda" },
  { label: "SaaS", value: "saas" },
  { label: "Service Agreement", value: "services" },
  { label: "Loan Agreement", value: "loan" },
  { label: "Lease", value: "lease" },
  { label: "Employment Contract", value: "employment" },
  { label: "Other", value: "other" },
] as const;

const CONTEXT_ROLE_OPTIONS = [
  { label: "Buyer", value: "buyer" },
  { label: "Seller", value: "seller" },
  { label: "Supplier", value: "supplier" },
  { label: "Customer", value: "customer" },
  { label: "Landlord", value: "landlord" },
  { label: "Tenant", value: "tenant" },
  { label: "Lender", value: "lender" },
  { label: "Borrower", value: "borrower" },
  { label: "Partner", value: "partner" },
  { label: "Licensor", value: "licensor" },
  { label: "Licensee", value: "licensee" },
  { label: "Employer", value: "employer" },
  { label: "Employee", value: "employee" },
  { label: "Other", value: "other" },
] as const;

const CRITICALITY_OPTIONS = [
  { label: "Low", value: "low" },
  { label: "Medium", value: "medium" },
  { label: "High", value: "high" },
  { label: "Mission critical", value: "mission_critical" },
] as const;

const RISK_POSTURE_OPTIONS = [
  { label: "Balanced", value: "balanced" },
  { label: "Conservative", value: "conservative" },
  { label: "Aggressive growth", value: "aggressive_growth" },
] as const;

const DATA_SENSITIVITY_OPTIONS = [
  { label: "Not applicable", value: "none" },
  { label: "Low", value: "low" },
  { label: "Moderate", value: "moderate" },
  { label: "High", value: "high" },
  { label: "Special category", value: "special_category" },
] as const;

const INSURANCE_OPTIONS = [
  { label: "Unknown", value: "unknown" },
  { label: "Not applicable", value: "not_applicable" },
  { label: "Not confirmed", value: "not_confirmed" },
  { label: "Confirmed", value: "confirmed" },
  { label: "Insufficient", value: "insufficient" },
] as const;

const REVIEW_PURPOSE_OPTIONS = [
  "Pre-signature review",
  "Negotiation preparation",
  "Renewal review",
  "Internal risk screen",
  "Supplier onboarding",
] as const;

function severityTone(severity?: number) {
  if ((severity ?? 0) >= 5) return "Critical";
  if ((severity ?? 0) >= 4) return "High";
  if ((severity ?? 0) >= 3) return "Moderate";
  return "Low";
}

function findingImpactGroup(finding: Finding): "Critical" | "High" | "Moderate" | "Low" {
  const severity = finding.severity ?? 0;
  if (severity >= 5) return "Critical";
  if (severity >= 4) return "High";
  if (severity >= 3) return "Moderate";
  return "Low";
}

function groupFindingTone(group: "Critical" | "High" | "Moderate" | "Low") {
  switch (group) {
    case "Critical":
      return {
        wrapper: "border-red-200 bg-red-50/70",
        badge: "border-red-200 bg-red-50 text-red-700",
        dot: "bg-red-500",
      };
    case "High":
      return {
        wrapper: "border-[#d8b36f] bg-[#fff6e4]",
        badge: "border-[#d8b36f] bg-[#fff4dc] text-[#7a4d12]",
        dot: "bg-[#b7791f]",
      };
    case "Moderate":
      return {
        wrapper: "border-[#dccaa8] bg-[#fffaf0]",
        badge: "border-[#dccaa8] bg-[#fcf2df] text-[#6f552d]",
        dot: "bg-[#b08d57]",
      };
    default:
      return {
        wrapper: "border-[#e8ddca] bg-[#fffdf8]",
        badge: "border-[#e8ddca] bg-[#fffdf8] text-neutral-500",
        dot: "bg-[#c8bca7]",
      };
  }
}

function synthesisLabel(value: string) {
  const text = value.replace(/^cross_/, "").replace(/^derived_cross_clause_/, "").replace(/_/g, " ");
  if (text.includes("renewal") || text.includes("auto renewal")) return "Renewal pressure pattern";
  if (text.includes("suspension") || text.includes("operational") || text.includes("lock")) return "Operational lock-in pattern";
  if (text.includes("jurisdiction") || text.includes("venue") || text.includes("forum")) return "Dispute burden stack";
  if (text.includes("data") || text.includes("confidentiality")) return "Data control tension";
  if (text.includes("liability") || text.includes("indemnity") || text.includes("cap")) return "Economic leverage cluster";
  if (text.includes("termination") || text.includes("refund")) return "Control asymmetry";
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function severityBadgeClass(severity: "LOW" | "MEDIUM" | "HIGH") {
  switch (severity) {
    case "HIGH":
      return "border-red-200 bg-red-50 text-red-700";
    case "MEDIUM":
      return "border-amber-200 bg-amber-50 text-amber-700";
    default:
      return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
}

function scoreBand(score: number, severity: "LOW" | "MEDIUM" | "HIGH") {
  if (severity === "HIGH") return "Elevated detected";
  if (severity === "MEDIUM") return score >= 35 ? "Elevated detected" : "Moderate detected";
  return score >= 20 ? "Moderate detected" : "Low detected";
}

const CATEGORY_PROFILES: Record<
  string,
  { focus: string; action: string; consequence: string }
> = {
  jurisdiction: {
    focus:
      "Reposition governing law and dispute forum into a venue your business can afford to use, enforce, and defend.",
    action: "Reposition dispute forum",
    consequence:
      "Dispute cost, enforcement friction, and legal leverage may move into a venue that is operationally disadvantageous.",
  },
  service: {
    focus:
      "Convert suspension rights from a pressure tool into a controlled remedy with objective triggers, notice, and restoration discipline.",
    action: "Control suspension mechanics",
    consequence:
      "Critical service access could be interrupted with limited warning, creating operational disruption and weak recovery leverage.",
  },
  payment: {
    focus:
      "Lock the commercial model so price, scope, or charging mechanics cannot drift after signature without your active consent.",
    action: "Freeze commercial drift",
    consequence:
      "Commercial exposure can widen after signature through price movement, margin erosion, or forced acceptance of new economics.",
  },
  liability: {
    focus:
      "Rebuild the exposure architecture so financial downside stays bounded, insurable, and proportionate to contract value.",
    action: "Rebuild liability architecture",
    consequence:
      "A single dispute or failure event could create outsized financial exposure beyond the expected value of the contract.",
  },
  indemnity: {
    focus:
      "Narrow indemnity so third-party and direct-loss exposure cannot be transferred onto your side beyond controlled, negotiated boundaries.",
    action: "Constrain indemnity transfer",
    consequence:
      "Third-party claims, losses, or litigation cost may be pushed disproportionately onto your business through one-sided indemnity allocation.",
  },
  termination: {
    focus:
      "Remove unilateral walk-away leverage or neutralize it with notice runway, cure rights, and transition protection.",
    action: "Neutralize exit asymmetry",
    consequence:
      "The counterparty may retain exit optionality while you remain committed, weakening revenue visibility and planning certainty.",
  },
};

const DEFAULT_CATEGORY_PROFILE = {
  focus:
    "Narrow broad drafting so discretion cannot later be weaponized into operational or commercial leverage.",
  action: "Narrow discretionary drafting",
  consequence:
    "Unchecked drafting can convert routine commercial dependency into asymmetric leverage against your business.",
};

const CONTROL_CATEGORIES = new Set(["service", "termination"]);
const DISPUTE_CATEGORIES = new Set(["jurisdiction"]);
const ECONOMIC_CATEGORIES = new Set(["payment", "liability", "indemnity"]);

function categoryProfile(category?: string) {
  if (!category) return DEFAULT_CATEGORY_PROFILE;
  return CATEGORY_PROFILES[category] ?? DEFAULT_CATEGORY_PROFILE;
}

function hasAnyCategory(categories: string[], group: Set<string>) {
  return categories.some((category) => group.has(category));
}

function recommendedFocus(category?: string) {
  return categoryProfile(category).focus;
}

function consequenceSummary(category?: string) {
  return categoryProfile(category).consequence;
}

function negotiationPriority(category?: string) {
  switch (category) {
    case "indemnity":
      return "Limit indemnity scope, covered losses, claim control, defence costs, and third-party exposure.";
    case "liability":
      return "Set proportionate liability caps, define carve-outs carefully, and avoid uncapped general exposure.";
    case "payment":
      return "Fix price-change rights, charging triggers, renewal economics, and any unilateral commercial variation.";
    case "termination":
      return "Add notice runway, cure rights, transition support, and balanced termination rights.";
    case "service":
      return "Constrain suspension rights with objective triggers, notice, proportionality, and restoration obligations.";
    case "jurisdiction":
      return "Move governing law, forum, and enforcement mechanics into a commercially usable venue.";
    default:
      return "Clarify broad drafting, remove discretionary leverage, and convert vague rights into objective controls.";
  }
}

function priorityReason(category?: string) {
  switch (category) {
    case "indemnity":
      return "Indemnity clauses can transfer claim burden faster than ordinary liability wording.";
    case "liability":
      return "Liability architecture determines whether a bad event stays bounded or becomes disproportionate.";
    case "payment":
      return "Commercial drift after signature can destroy expected margin even when service delivery looks stable.";
    case "termination":
      return "Exit asymmetry gives one side optionality while the other carries planning risk.";
    case "service":
      return "Suspension mechanics can become operational leverage if not tied to disciplined triggers.";
    case "jurisdiction":
      return "A hostile or impractical forum can make even strong rights expensive to enforce.";
    default:
      return "Broad or vague drafting often becomes leverage only after dependency has formed.";
  }
}

function executiveSummary(
  severity: "LOW" | "MEDIUM" | "HIGH",
  riskCount: number,
  categories: string[],
  primaryCategory?: string,
) {
  const uniqueCategories = Array.from(new Set(categories.filter(Boolean)));
  const hasControlRisk = hasAnyCategory(uniqueCategories, CONTROL_CATEGORIES);
  const hasDisputeRisk = hasAnyCategory(uniqueCategories, DISPUTE_CATEGORIES);
  const hasEconomicRisk = hasAnyCategory(uniqueCategories, ECONOMIC_CATEGORIES);
  const areaLabel = `${riskCount} priority risk area${riskCount === 1 ? "" : "s"}`;

  if (severity === "HIGH") {
    if (riskCount >= 3 && hasControlRisk && hasEconomicRisk && hasDisputeRisk) {
      return `This contract presents material structural exposure because commercial downside, operational leverage, and dispute positioning all appear to accumulate with the counterparty. ${areaLabel} should be addressed before acceptance.`;
    }
    if (riskCount >= 2 && hasControlRisk && hasEconomicRisk) {
      return `This contract presents material structural exposure because the counterparty appears to hold both economic leverage and control over continuity or exit. ${areaLabel} should be addressed before acceptance.`;
    }
    if (riskCount >= 2 && hasControlRisk && hasDisputeRisk) {
      return `This contract presents material structural exposure because counterparty-favored control rights are reinforced by unfavorable dispute positioning. ${areaLabel} should be addressed before acceptance.`;
    }
    if (riskCount >= 2 && hasEconomicRisk && hasDisputeRisk) {
      return `This contract presents material structural exposure because downside economics appear difficult to resist and expensive to enforce in dispute. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "indemnity") {
      return `This contract presents material downside exposure because indemnity structure appears capable of transferring claim and cost burden onto your side. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "liability") {
      return `This contract presents material downside exposure because liability architecture appears misaligned with practical deal value and insurable risk. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "payment") {
      return `This contract presents material commercial exposure because the counterparty appears able to move pricing or charging mechanics after signature. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "termination") {
      return `This contract presents material control risk because exit optionality appears to sit disproportionately with the counterparty. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "service") {
      return `This contract presents material operational exposure because service continuity appears vulnerable to counterparty-controlled interruption rights. ${areaLabel} should be addressed before acceptance.`;
    }
    if (primaryCategory === "jurisdiction") {
      return `This contract presents material dispute exposure because venue and enforcement mechanics appear structurally unfavorable. ${areaLabel} should be addressed before acceptance.`;
    }
    return `This contract presents material structural exposure. ${areaLabel} should be addressed before acceptance.`;
  }

  if (severity === "MEDIUM") {
    if (primaryCategory === "jurisdiction") {
      return "The scan identified a dispute forum / governing-law signal that may affect enforcement cost, venue burden, and escalation planning.";
    }
    if (hasControlRisk && hasEconomicRisk) {
      return "This contract contains meaningful structural exposure because economic pressure and control rights appear to reinforce each other in the counterparty's favor.";
    }
    if (hasControlRisk && hasDisputeRisk) {
      return "This contract contains meaningful structural exposure because control rights may be difficult to resist once dispute mechanics also favor the counterparty.";
    }
    if (hasEconomicRisk && hasDisputeRisk) {
      return "This contract contains meaningful structural exposure because commercial downside may be harder to challenge under the current dispute framework.";
    }
    return "This contract contains meaningful downside exposure. The current drafting is negotiable, but not clean enough for passive acceptance.";
  }

  if (hasControlRisk && hasEconomicRisk) {
    return "Current rule detection shows no major structural alert, but the contract still deserves a final check for combined control and commercial dependency.";
  }

  if (riskCount > 0 && primaryCategory === "jurisdiction") {
    return "The scan identified a dispute forum / governing-law signal that may affect enforcement cost, venue burden, and escalation planning.";
  }

  if (riskCount > 0) {
    return "The scan identified limited but reviewable contract risk signals. Treat the result as structured review support, not as contract approval.";
  }

  return "Current rule detection shows limited structural risk, but final acceptance should still depend on business dependency, leverage, and off-text commercial reality.";
}

function decisionPosture(
  severity: "LOW" | "MEDIUM" | "HIGH",
  topRiskCount: number,
  categories: string[],
  primaryCategory?: string,
): DecisionPostureDisplay {
  const uniqueCategories = Array.from(new Set(categories.filter(Boolean)));
  const hasControlRisk = hasAnyCategory(uniqueCategories, CONTROL_CATEGORIES);
  const hasDisputeRisk = hasAnyCategory(uniqueCategories, DISPUTE_CATEGORIES);
  const hasEconomicRisk = hasAnyCategory(uniqueCategories, ECONOMIC_CATEGORIES);
  const areaLabel = `${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}`;

  if (severity === "HIGH") {
    if (topRiskCount >= 3 && hasControlRisk && hasEconomicRisk && hasDisputeRisk) {
      return {
        label: "Hold / Renegotiate",
        detail:
          "Do not accept in current form. The contract appears to combine commercial downside, operational leverage, and unfavorable dispute positioning in a way that compounds counterparty advantage.",
        nextStep:
          "Start with the highest-ranked clause, then remove the combined pattern of economic drift, control leverage, and adverse dispute mechanics.",
      };
    }
    if (primaryCategory === "jurisdiction") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Venue and enforcement mechanics appear structurally unfavorable across ${areaLabel}.`,
        nextStep:
          "Move governing law and dispute venue into a forum your business can realistically use, defend, and enforce.",
      };
    }
    return {
      label: "Hold / Renegotiate",
      detail:
        "Do not accept in current form. Structural exposure remains material on current rule detection.",
      nextStep:
        "Escalate the priority findings into redlines before the agreement moves forward.",
    };
  }

  if (severity === "MEDIUM") {
    if (primaryCategory === "jurisdiction") {
      return {
        label: "Proceed with Negotiation",
        detail:
          "The scan identified a dispute forum / governing-law signal that may affect enforcement cost, venue burden, and escalation planning.",
        nextStep:
          "Confirm whether the selected governing law, jurisdiction, or venue is commercially workable before approval.",
      };
    }
    return {
      label: "Proceed with Negotiation",
      detail:
        "The contract is not clean enough for passive acceptance. Meaningful structural issues are present, but they still appear negotiable.",
      nextStep:
        "Use the priority risks to focus redlines on the clauses most likely to create leverage or downside.",
    };
  }

  if (hasControlRisk && hasEconomicRisk) {
    return {
      label: "Proceed with Standard Review",
      detail:
        "No material automated risk signal was elevated in the reviewed text. This should be treated as a low-signal automated result, not as contract approval.",
      nextStep:
        "Continue normal commercial review and confirm no external business dependency changes the risk position.",
    };
  }

  if (topRiskCount > 0 && primaryCategory === "jurisdiction") {
    return {
      label: "Proceed with Standard Review",
      detail:
        "The scan identified a dispute forum / governing-law signal that may affect enforcement cost, venue burden, and escalation planning.",
      nextStep:
        "Confirm whether the selected governing law, jurisdiction, or venue is commercially workable before approval.",
    };
  }

  if (topRiskCount > 0) {
    return {
      label: "Proceed with Standard Review",
      detail:
        "The scan identified limited but reviewable contract risk signals. This should be treated as structured review support, not as contract approval.",
      nextStep:
        "Check the priority findings before final acceptance and escalate if the practical business consequence is material.",
    };
  }

  return {
    label: "Low-Signal Automated Review",
    detail:
      "No governed risk signal was elevated by the current rule set. This is a low-signal automated result, not a contract clearance outcome. Review may still be required for off-text commercial dependency, unusual drafting, missing protections, sector-specific obligations, or risks outside current rule coverage.",
    nextStep:
      "Use this as review triage only: confirm the commercial context, missing protections, and any sector-specific obligations before acceptance.",
  };
}

function postureLabel(value?: string | null) {
  if (!value) return "";
  return value
    .replace(/_/g, " ")
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function backendDecisionPosture(result: AnalyzeResult | null): DecisionPostureDisplay | null {
  if (!result) return null;
  const snapshot = result.meta?.decision_intelligence ?? null;
  const code =
    result.decision_posture_code ||
    result.decision_posture ||
    result.meta?.decision_posture ||
    snapshot?.decision_posture_code ||
    null;
  if (!code) return null;
  const rationale = result.posture_rationale ?? result.meta?.posture_rationale ?? snapshot?.posture_rationale ?? [];
  const summary = snapshot?.decision_posture_summary;
  return {
    label: postureLabel(code),
    detail:
      rationale[0] ||
      summary ||
      "Deterministic findings, context, and configured tolerance have been converted into a management review posture.",
    nextStep:
      result.recommended_next_step ||
      result.meta?.recommended_next_step ||
      snapshot?.recommended_next_step ||
      "Review the linked evidence and record the commercial decision before proceeding.",
    escalationReason:
      result.escalation_reason ||
      result.meta?.escalation_reason ||
      snapshot?.escalation_reason ||
      null,
  };
}

function formatReportTimestamp(timestamp?: string | null) {
  if (!timestamp) return "Not generated";

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(timestamp));
}

type ReliabilityLabel = "Strong" | "Moderate" | "Limited" | "Low signal";

function reviewReliability(confidence?: number | null): { label: ReliabilityLabel; helper: string } {
  if (typeof confidence !== "number" || Number.isNaN(confidence) || confidence <= 0) {
    return {
      label: "Limited",
      helper: "Some text may not have been captured clearly. Check clause evidence before relying on the result.",
    };
  }

  if (confidence >= 0.85) {
    return {
      label: "Strong",
      helper: "The submitted text was clear enough for a reliable automated review.",
    };
  }

  if (confidence >= 0.6) {
    return {
      label: "Moderate",
      helper: "The review is usable, but some wording or extraction quality may need checking.",
    };
  }

  return {
    label: "Limited",
    helper: "Some text may not have been captured clearly. Check clause evidence before relying on the result.",
  };
}

function decisionPrimaryRiskTypeLabel(category?: string | null) {
  switch (category) {
    case "jurisdiction":
      return "Dispute forum / jurisdiction";
    case "liability":
      return "Liability exposure";
    case "data":
      return "Data governance";
    case "indemnity":
      return "Risk transfer / indemnity";
    case "termination":
      return "Exit rights / termination";
    case "payment":
    case "service":
      return "Operational continuity / cash flow";
    default:
      return category ? category.replace(/_/g, " ") : "Contract risk signal";
  }
}

function decisionImpactAreaLabel(category?: string | null) {
  switch (category) {
    case "jurisdiction":
      return "Enforcement / Cost / Venue";
    case "liability":
      return "Financial exposure / Cap limits";
    case "data":
      return "Data governance / Usage rights";
    case "indemnity":
      return "Risk transfer / Defence exposure";
    case "termination":
      return "Exit rights / Continuity";
    case "payment":
    case "service":
      return "Operational continuity / Cash flow";
    default:
      return "Commercial contract exposure";
  }
}

function decisionConfidenceDriverLabel(
  leadRuleId: string,
  reliabilityLabel: ReliabilityLabel,
  matchedLocation?: string | null,
) {
  const locationSuffix = matchedLocation ? `: ${matchedLocation}` : "";

  switch (leadRuleId) {
    case "governing_law_foreign_or_unfamiliar":
      return `Explicit governing law clause detected${locationSuffix}`;
    case "jurisdiction_exclusive_foreign_forum":
      return `Exclusive jurisdiction clause explicitly defined${locationSuffix}`;
    case "jurisdiction_non_exclusive_forum":
      return `Non-exclusive jurisdiction language detected${locationSuffix}`;
    case "arbitration_forum_or_seat":
      return matchedLocation
        ? `Arbitration seat specified: ${matchedLocation}`
        : "Arbitration forum or seat language detected";
    case "venue_burden_foreign_court":
      return matchedLocation
        ? `Dispute venue language explicitly detected: ${matchedLocation}`
        : "Dispute venue language explicitly detected";
    default:
      if (reliabilityLabel === "Strong") {
        return "Direct clause match with explicit contractual language";
      }
      if (reliabilityLabel === "Moderate") {
        return "Pattern-based detection with moderate certainty";
      }
      return "Review against clause evidence before relying on the signal";
  }
}


function findingDecisionId(finding: Finding, index: number) {
  return (finding.rule_id || `${finding.category || "finding"}-${index}`).slice(0, 120);
}

function policyIndicator(finding: Finding): { label: string; className: string; detail: string } | null {
  const status = finding.policy_status;
  if (!status) return null;

  if (status === "exceeds_tolerance") {
    return {
      label: "Outside your organisation's tolerance",
      className: "border-red-200 bg-red-50 text-red-700",
      detail: finding.policy_explanation || "This finding appears outside the configured tolerance for this risk family.",
    };
  }

  if (status === "conflicts_with_policy") {
    return {
      label: "Conflicts with configured policy",
      className: "border-amber-200 bg-amber-50 text-amber-800",
      detail: finding.policy_explanation || "This finding conflicts with the configured organisation policy.",
    };
  }

  if (status === "within_tolerance") {
    return {
      label: "Within configured policy",
      className: "border-emerald-200 bg-emerald-50 text-emerald-700",
      detail: finding.policy_explanation || "This finding appears within configured tolerance, but evidence should still be documented.",
    };
  }

  if (status === "policy_unknown") {
    return {
      label: "No policy configured for this risk family",
      className: "border-[#dccaa8] bg-[#fffaf0] text-[#6f552d]",
      detail: finding.policy_explanation || "No organisation tolerance has been configured for this risk family.",
    };
  }

  return null;
}

function findingDecisionLabel(value?: string | null) {
  return FINDING_DECISION_OPTIONS.find((option) => option.value === value)?.label ?? "Unresolved";
}

function scanDecisionLabel(value?: string | null) {
  return SCAN_DECISION_OPTIONS.find((option) => option.value === value)?.label ?? "Pending";
}

function acceptableGuidance(finding: Finding): string[] {
  if (finding.decision_guidance?.length) return finding.decision_guidance;

  const category = (finding.category || "").toLowerCase();
  const text = `${finding.rule_id || ""} ${finding.title || ""}`.toLowerCase();

  if (category === "liability" || text.includes("liability")) {
    return ["Add or raise the liability cap", "Remove broad carve-outs", "Make the cap mutual"];
  }
  if (category === "indemnity" || text.includes("indemn")) {
    return ["Narrow indemnity scope", "Cap indemnity exposure", "Make the indemnity mutual"];
  }
  if (category === "data" || text.includes("data")) {
    return ["Remove AI training rights", "Restrict onward sharing", "Add confidentiality survival"];
  }
  if (category === "termination" || text.includes("termination") || text.includes("renewal")) {
    return ["Add notice", "Add a cure period", "Add refund or credit rights", "Add transition support"];
  }
  if (category === "payment" || category === "service" || text.includes("suspension") || text.includes("payment")) {
    return ["Limit suspension rights", "Add a disputed-sums carve-out", "Add restoration obligations"];
  }
  if (category === "jurisdiction" || text.includes("forum") || text.includes("governing")) {
    return ["Align governing law and forum with operational reality", "Confirm enforcement cost and venue burden", "Escalate if forum leverage is asymmetric"];
  }

  return ["Narrow broad discretion", "Add objective triggers", "Document the commercial exception if accepted"];
}

function lowSignalSummary() {
  return "No material automated risk signal was elevated in the reviewed text. This should be treated as a low-signal automated result, not as contract approval.";
}

function normalizeAIExplainSeverity(severity: string | undefined) {
  const normalized = String(severity || "").trim().toUpperCase();
  if (normalized === "LOW" || normalized === "MEDIUM" || normalized === "HIGH") return normalized;
  if (normalized.includes("HIGH")) return "HIGH";
  if (normalized.includes("MEDIUM")) return "MEDIUM";
  return "LOW";
}

function optionalNumber(value: unknown) {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

const EXPOSURE_SCORE_MAX_RISK_SCORE = 200;

function clampExposureScore(value: number) {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function exposureScoreFromStoredRiskScore(value: number) {
  return clampExposureScore((value / EXPOSURE_SCORE_MAX_RISK_SCORE) * 100);
}

function scanHistoryExposureScore(scan: ScanHistoryItem) {
  const explicit = optionalNumber(scan.normalized_score) ?? optionalNumber(scan.meta?.normalized_score);
  if (explicit !== undefined) return clampExposureScore(explicit);

  const storedScore = optionalNumber(scan.risk_score);
  if (storedScore === undefined) return null;

  return exposureScoreFromStoredRiskScore(storedScore);
}

function buildAIExplainPayload(result: AnalyzeResult) {
  return {
    normalized_score: result.meta?.normalized_score ?? exposureScoreFromStoredRiskScore(result.risk_score),
    severity: normalizeAIExplainSeverity(result.severity),
    flags: result.flags ?? [],
    findings: (result.findings ?? []).map((finding) => ({
      rule_id: finding.rule_id,
      title: finding.title,
      category: finding.category,
      severity: optionalNumber(finding.severity),
      rationale: finding.rationale,
      matched_text: finding.matched_text,
    })),
    meta: {
      confidence: result.meta?.confidence ?? result.confidence_hint ?? null,
      top_risks: (result.meta?.top_risks ?? []).map((risk) => ({
        rule_id: risk.rule_id,
        title: risk.title,
        category: risk.category,
        severity: optionalNumber(risk.severity),
        weight: optionalNumber(risk.weight),
      })),
      matched_rule_count: result.meta?.matched_rule_count ?? result.findings?.length ?? 0,
      suppressed_rule_count: result.meta?.suppressed_rule_count ?? 0,
      contradiction_count: result.meta?.contradiction_count ?? 0,
    },
    source_type: result.source_type ?? null,
    extraction_method: result.extraction_method ?? null,
    confidence_hint: result.confidence_hint ?? null,
    has_extractable_text: result.has_extractable_text ?? null,
  };
}

function stripExtension(value: string) {
  return value.replace(/\.[^.]+$/, "");
}

function sanitizeFilenameSegment(value: string) {
  return value
    .replace(/[^\w\s-]/g, "")
    .replace(/\s+/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 60);
}

function readableSourceType(value?: string | null) {
  if (!value) return "Text";
  if (value === "file") return "File";
  if (value === "text") return "Text";
  if (value === "pdf") return "PDF";
  if (value === "image") return "Image";
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function readableExtractionMethod(value?: string | null) {
  if (!value) return "Direct review";
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function titleCaseReviewLabel(value: string) {
  return value
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function meaningfulScanTitle(value?: string | null) {
  const title = (value ?? "").trim();
  if (!title) return "";
  const normalized = title.toLowerCase();
  if (normalized.includes("untitled") || normalized === "stored contract risk review") return "";
  return title;
}

function scanHistoryDisplayTitle(scan: ScanHistoryItem, severity: "LOW" | "MEDIUM" | "HIGH") {
  const explicitTitle = meaningfulScanTitle(scan.source_title);
  if (explicitTitle) return explicitTitle;

  const contractType = typeof scan.context_profile_snapshot?.contract_type === "string"
    ? scan.context_profile_snapshot.contract_type
    : "";
  if (contractType && contractType.toLowerCase() !== "unknown") {
    return `${titleCaseReviewLabel(contractType)} review`;
  }

  if (scan.source_type && scan.source_type !== "unknown") {
    return `${readableSourceType(scan.source_type)} review`;
  }

  if (scan.created_at) {
    return `${titleCaseReviewLabel(severity.toLowerCase())}-risk review - ${formatReportTimestamp(scan.created_at)}`;
  }

  return "Contract review";
}

function extractCustomerError(raw: string) {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.error === "string") return parsed.error;
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (typeof parsed?.detail?.error === "string") return parsed.detail.error;
  } catch {
    return "The review could not be completed. Please check the source text or upload and try again.";
  }
  return "The review could not be completed. Please check the source text or upload and try again.";
}

function coerceAIReviewSummary(value?: AIReviewSummary | string | null): AIReviewSummary | null {
  if (!value) return null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed ? { raw_text: trimmed } : null;
  }
  return value;
}

function hasAISectionText(value?: string | null) {
  return Boolean(value?.trim());
}

const AI_BOUNDARY_FALLBACK = "AI Review Notes explain deterministic VoxaRisk findings only. They do not change the score, severity, findings, or decision posture, and they are not legal advice.";

const AI_SECTION_HEADINGS: Record<string, { heading: string; kind: AIReviewDisplaySection["kind"] }> = {
  "executive overview": { heading: "Executive overview", kind: "paragraph" },
  overview: { heading: "Executive overview", kind: "paragraph" },
  "primary risk drivers": { heading: "Primary risk drivers", kind: "bullets" },
  "key risk drivers": { heading: "Primary risk drivers", kind: "bullets" },
  "recommended review focus": { heading: "Recommended review focus", kind: "bullets" },
  "suggested review focus": { heading: "Recommended review focus", kind: "bullets" },
  "negotiation focus": { heading: "Recommended review focus", kind: "bullets" },
  "evidence signals": { heading: "Evidence signals", kind: "bullets" },
  "evidence notes": { heading: "Evidence signals", kind: "bullets" },
  "uncertainty notes": { heading: "Evidence signals", kind: "bullets" },
  "boundary note": { heading: "Boundary note", kind: "boundary" },
  "boundary notice": { heading: "Boundary note", kind: "boundary" },
};

function cleanAIReviewItem(value?: string | null) {
  return (value ?? "")
    .replace(/^[-*\d.)\s]+/, "")
    .replace(/\s+/g, " ")
    .trim();
}

function addAISectionItem(sections: AIReviewDisplaySection[], heading: string, kind: AIReviewDisplaySection["kind"], value?: string | null) {
  const item = cleanAIReviewItem(value);
  if (!item) return;

  let section = sections.find((candidate) => candidate.heading === heading);
  if (!section) {
    section = { heading, kind, items: [] };
    sections.push(section);
  }
  if (!section.items.includes(item)) {
    section.items.push(item);
  }
}

function normalizeAIHeading(value: string) {
  return value
    .replace(/[:?-]+$/g, "")
    .replace(/^#+\s*/, "")
    .trim()
    .toLowerCase();
}

function sectionForAIHeading(value: string) {
  const normalized = normalizeAIHeading(value);
  if (normalized === "ai review") return null;
  return AI_SECTION_HEADINGS[normalized];
}

function splitAISentences(rawText?: string | null) {
  return (rawText ?? "")
    .split(/\n+|(?<=[.!?])\s+(?=[A-Z])/)
    .map(cleanAIReviewItem)
    .filter(Boolean);
}

function isBoundaryAIText(value: string) {
  const lower = value.toLowerCase();
  return lower.includes("not legal advice") || lower.includes("legal opinion") || lower.includes("contract approval") || lower.includes("guarantee");
}

function isRiskDriverText(value: string) {
  const lower = value.toLowerCase();
  return [
    "risk",
    "exposure",
    "liability",
    "indemnity",
    "termination",
    "refund",
    "data",
    "confidentiality",
    "suspension",
    "payment",
    "jurisdiction",
    "governing law",
    "score",
  ].some((term) => lower.includes(term));
}

function isReviewFocusText(value: string) {
  const lower = value.toLowerCase();
  return ["review", "negotiate", "narrow", "limit", "add", "remove", "align", "escalate", "confirm", "focus"].some((term) => lower.includes(term));
}

function isEvidenceText(value: string) {
  const lower = value.toLowerCase();
  return ["evidence", "deterministic", "finding", "clause", "signal", "matched"].some((term) => lower.includes(term));
}

function parseStructuredAIText(rawText?: string | null) {
  const sections: AIReviewDisplaySection[] = [];
  let current: AIReviewDisplaySection | null = null;
  const unassigned: string[] = [];

  for (const rawLine of (rawText ?? "").split(/\n+/)) {
    const line = rawLine.trim();
    if (!line) continue;

    const heading = sectionForAIHeading(line);
    if (heading) {
      current = sections.find((section) => section.heading === heading.heading) ?? null;
      if (!current) {
        current = { heading: heading.heading, kind: heading.kind, items: [] };
        sections.push(current);
      }
      continue;
    }

    const item = cleanAIReviewItem(line);
    if (!item) continue;
    if (current) {
      addAISectionItem(sections, current.heading, current.kind, item);
    } else {
      unassigned.push(item);
    }
  }

  const populated = sections.filter((section) => section.items.length > 0);
  if (populated.length) return populated;
  if (!unassigned.length) return [];

  addAISectionItem(sections, "Executive overview", "paragraph", unassigned[0]);
  unassigned.slice(1).forEach((item) => addAISectionItem(sections, "Primary risk drivers", "bullets", item));
  return sections.filter((section) => section.items.length > 0);
}

function formatAIReviewSections(summary?: AIReviewSummary | null): AIReviewDisplaySection[] {
  if (!summary) return [];

  const sections: AIReviewDisplaySection[] = [];
  addAISectionItem(sections, "Executive overview", "paragraph", summary.executive_overview ?? summary.overview);
  (summary.primary_risk_drivers ?? []).forEach((item) => addAISectionItem(sections, "Primary risk drivers", "bullets", item));
  (summary.recommended_review_focus ?? summary.negotiation_focus ?? []).forEach((item) => addAISectionItem(sections, "Recommended review focus", "bullets", item));
  (summary.evidence_signals ?? []).forEach((item) => addAISectionItem(sections, "Evidence signals", "bullets", item));
  (summary.evidence_notes ?? []).forEach((note) => {
    addAISectionItem(sections, "Evidence signals", "bullets", [note.title, note.explanation, note.evidence_excerpt].filter(Boolean).join(": "));
  });
  (summary.uncertainty_notes ?? []).forEach((item) => addAISectionItem(sections, "Evidence signals", "bullets", item));

  const structuredBoundary = summary.boundary_note ?? summary.boundary_notice;
  if (structuredBoundary) {
    addAISectionItem(sections, "Boundary note", "boundary", structuredBoundary);
  }

  if (sections.length === 0 && hasAISectionText(summary.raw_text)) {
    const parsed = parseStructuredAIText(summary.raw_text);
    if (parsed.length) {
      sections.push(...parsed);
    } else {
      const items = splitAISentences(summary.raw_text);
      const boundaryItems = items.filter(isBoundaryAIText);
      const contentItems = items.filter((item) => !isBoundaryAIText(item));
      const [overview, ...remaining] = contentItems;

      addAISectionItem(sections, "Executive overview", "paragraph", overview);
      const riskDrivers = remaining.filter(isRiskDriverText).slice(0, 5);
      const reviewFocus = remaining.filter(isReviewFocusText).slice(0, 4);
      const evidenceSignals = remaining.filter(isEvidenceText).slice(0, 4);

      (riskDrivers.length ? riskDrivers : remaining.slice(0, 4)).forEach((item) => addAISectionItem(sections, "Primary risk drivers", "bullets", item));
      reviewFocus.forEach((item) => addAISectionItem(sections, "Recommended review focus", "bullets", item));
      evidenceSignals.forEach((item) => addAISectionItem(sections, "Evidence signals", "bullets", item));
      boundaryItems.forEach((item) => addAISectionItem(sections, "Boundary note", "boundary", item));
    }
  }

  if (!sections.some((section) => section.heading === "Boundary note")) {
    addAISectionItem(sections, "Boundary note", "boundary", AI_BOUNDARY_FALLBACK);
  }

  const sectionOrder = ["Executive overview", "Primary risk drivers", "Recommended review focus", "Evidence signals", "Boundary note"];
  return sections
    .filter((section) => section.items.length > 0)
    .sort((left, right) => sectionOrder.indexOf(left.heading) - sectionOrder.indexOf(right.heading));
}

function renderAITextWithEmphasis(text: string): ReactNode {
  const emphasisPattern = /(termination without refund|broad data rights|weak confidentiality|broad indemnity|low liability cap|supplier suspension|upfront payment|no refund|ai training|onward sharing|liability cap|indemnity|termination|confidentiality|data rights|suspension rights)/gi;
  return text.split(emphasisPattern).map((part, index) => {
    if (index % 2 === 1) {
      return <strong key={`${part}-${index}`} className="font-semibold text-neutral-950">{part}</strong>;
    }
    return part;
  });
}

function normalizeAIExplainResponse(payload: AIExplainResponse | null): NormalizedAIExplainResponse | AIExplainResponse | null {
  if (!payload) return null;

  const summary =
    coerceAIReviewSummary(payload.ai_summary) ??
    coerceAIReviewSummary(payload.summary) ??
    coerceAIReviewSummary(payload.ai_review) ??
    coerceAIReviewSummary(payload.review_notes) ??
    coerceAIReviewSummary(payload.data?.ai_summary) ??
    coerceAIReviewSummary(payload.data?.summary);

  const directSummary =
    !summary && (
      payload.executive_overview ||
      payload.primary_risk_drivers ||
      payload.recommended_review_focus ||
      payload.evidence_signals ||
      payload.overview ||
      payload.risk_posture_summary
    )
      ? {
          executive_overview: payload.executive_overview,
          primary_risk_drivers: payload.primary_risk_drivers,
          recommended_review_focus: payload.recommended_review_focus,
          evidence_signals: payload.evidence_signals,
          boundary_note: payload.boundary_note,
          overview: payload.overview,
          risk_posture_summary: payload.risk_posture_summary,
          negotiation_focus: payload.negotiation_focus,
          evidence_notes: payload.evidence_notes,
          uncertainty_notes: payload.uncertainty_notes,
          boundary_notice: payload.boundary_notice,
        }
      : null;

  const aiSummary = summary ?? directSummary;

  if (!aiSummary) return payload;

  return {
    ...payload,
    status: "available",
    ai_summary: aiSummary,
  } as NormalizedAIExplainResponse;
}

export default function DashboardPage() {
  const [authState, setAuthState] = useState<AuthState>("loading");
  const [accountContext, setAccountContext] = useState<DashboardAccountContext | null>(null);
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<"text" | "file">("text");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLabel, setUploadLabel] = useState("No file selected");
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);
  const [reportTitle, setReportTitle] = useState("");
  const [preparedFor, setPreparedFor] = useState("");
  const [documentType, setDocumentType] = useState("");
  const [reviewPurpose, setReviewPurpose] = useState("");
  const [contextUserRole, setContextUserRole] = useState("");
  const [criticalityLevel, setCriticalityLevel] = useState("");
  const [riskPosture, setRiskPosture] = useState("balanced");
  const [dealValue, setDealValue] = useState("");
  const [industry, setIndustry] = useState("");
  const [jurisdiction, setJurisdiction] = useState("");
  const [dataSensitivity, setDataSensitivity] = useState("");
  const [insuranceCoverage, setInsuranceCoverage] = useState("");
  const [internalReference, setInternalReference] = useState("");
  const [reportValidationMessage, setReportValidationMessage] = useState<string | null>(null);
  const [aiReview, setAIReview] = useState<NormalizedAIExplainResponse | null>(null);
  const [aiState, setAIState] = useState<
    "idle" | "loading" | "available" | "disabled" | "unavailable" | "denied" | "error"
  >("idle");
  const [aiMessage, setAIMessage] = useState<string | null>(null);
  const [scanHistory, setScanHistory] = useState<ScanHistoryItem[]>([]);
  const [recurringFamilies, setRecurringFamilies] = useState<Array<{ family: string; count: number }>>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [scanDecision, setScanDecision] = useState<ScanDecisionState>({ state: "pending" });
  const [findingDecisions, setFindingDecisions] = useState<Record<string, FindingDecisionState>>({});
  const [decisionNotesOpen, setDecisionNotesOpen] = useState<Record<string, boolean>>({});
  const [findingDecisionNotes, setFindingDecisionNotes] = useState<Record<string, string>>({});
  const [decisionSavingKey, setDecisionSavingKey] = useState<string | null>(null);
  const [decisionMessage, setDecisionMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const previousTitleRef = useRef<string | null>(null);

  async function loadScanHistory(): Promise<ScanHistoryResponse | null> {
    setHistoryLoading(true);
    try {
      const response = await fetch("/api/account/scans", { cache: "no-store" });
      if (!response.ok) return null;
      const payload: ScanHistoryResponse = await response.json();
      setScanHistory(payload.scans ?? []);
      setRecurringFamilies(payload.recurring_clause_families ?? []);
      return payload;
    } catch {
      setScanHistory([]);
      setRecurringFamilies([]);
      return null;
    } finally {
      setHistoryLoading(false);
    }
  }

  async function reopenStoredScan(scanId: string) {
    try {
      const response = await fetch(`/api/account/scans/${encodeURIComponent(scanId)}`, { cache: "no-store" });
      if (!response.ok) return;
      const detail: ScanHistoryItem = await response.json();
      const decisionMap = Object.fromEntries(
        (detail.finding_decisions ?? [])
          .filter((item) => item.finding_id)
          .map((item) => [String(item.finding_id), item]),
      );
      setActiveScanId(detail.id);
      setScanDecision(detail.decision_state ?? { state: "pending" });
      setFindingDecisions(decisionMap);
      setDecisionMessage(null);
      const severity =
        detail.severity === "HIGH" || detail.severity === "MEDIUM" || detail.severity === "LOW"
          ? detail.severity
          : "LOW";
      const exposureScore = scanHistoryExposureScore(detail);
      const intelligenceSnapshot = detail.decision_intelligence_snapshot ?? null;
      setResult({
        risk_score: detail.risk_score,
        severity,
        flags: detail.clause_families_detected ?? [],
        findings: detail.top_findings ?? [],
        meta: {
          normalized_score: exposureScore ?? detail.risk_score,
          confidence: detail.confidence ?? 0,
          matched_rule_count: detail.top_findings?.length ?? 0,
          top_risks: detail.top_findings ?? [],
          rule_families_detected: detail.clause_families_detected ?? [],
          synthesis_patterns_triggered: detail.synthesis_patterns_triggered ?? [],
          context_profile_used: detail.context_profile_snapshot ?? null,
          decision_intelligence: intelligenceSnapshot,
          decision_posture: intelligenceSnapshot?.decision_posture_code ?? null,
          posture_rationale: intelligenceSnapshot?.posture_rationale ?? [],
          recommended_next_step: intelligenceSnapshot?.recommended_next_step ?? null,
          escalation_reason: intelligenceSnapshot?.escalation_reason ?? null,
        },
        decision_posture: intelligenceSnapshot?.decision_posture_code ?? null,
        posture_rationale: intelligenceSnapshot?.posture_rationale ?? [],
        recommended_next_step: intelligenceSnapshot?.recommended_next_step ?? null,
        escalation_reason: intelligenceSnapshot?.escalation_reason ?? null,
        source_type: detail.source_type ?? "unknown",
      });
      setReportGeneratedAt(detail.created_at ?? new Date().toISOString());
      setReportTitle(scanHistoryDisplayTitle(detail, severity));
      resetAIReview();
    } catch {
      setErrorMessage("Stored review could not be reopened.");
    }
  }

  useEffect(() => {
    let cancelled = false;

    async function loadAccountContext() {
      try {
        const response = await fetch("/api/account/me", { cache: "no-store" });
        if (cancelled) return;
        if (response.ok) {
          const payload: DashboardAccountContext = await response.json();
          if (cancelled) return;
          setAccountContext(payload);
          setAuthState("authenticated");
          void loadScanHistory();
          return;
        }
        setAccountContext(null);
        setAuthState("unauthenticated");
      } catch {
        if (cancelled) return;
        setAccountContext(null);
        setAuthState("unauthenticated");
      }
    }

    void loadAccountContext();

    const restoreTitle = () => {
      if (previousTitleRef.current !== null) {
        document.title = previousTitleRef.current;
        previousTitleRef.current = null;
      }
    };

    window.addEventListener("afterprint", restoreTitle);
    return () => {
      cancelled = true;
      window.removeEventListener("afterprint", restoreTitle);
      restoreTitle();
    };
  }, []);

  function resetAIReview() {
    setAIReview(null);
    setAIState("idle");
    setAIMessage(null);
  }

  function resetResultState() {
    setResult(null);
    setReportGeneratedAt(null);
    setReportValidationMessage(null);
    setActiveScanId(null);
    setScanDecision({ state: "pending" });
    setFindingDecisions({});
    setDecisionNotesOpen({});
    setFindingDecisionNotes({});
    setDecisionMessage(null);
    resetAIReview();
  }

  function handleFileSelection(file: File | null) {
    resetResultState();
    setErrorMessage(null);
    setSelectedFile(file);

    if (!file) {
      setUploadLabel("No file selected");
      return;
    }

    setText("");
    setInputMode("file");
    setUploadLabel(file.name);
  }

  function onFileInputChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0] ?? null;
    handleFileSelection(file);
  }

  function clearUpload() {
    setSelectedFile(null);
    setUploadLabel("No file selected");
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (cameraInputRef.current) cameraInputRef.current.value = "";
    if (!text.trim()) {
      setInputMode("text");
    }
  }

  function contextPayload() {
    return {
      user_role: contextUserRole || undefined,
      contract_type: documentType || undefined,
      criticality_level: criticalityLevel || undefined,
      risk_posture: riskPosture || undefined,
      deal_value: dealValue.trim() || undefined,
      industry: industry.trim() || undefined,
      jurisdiction: jurisdiction.trim() || undefined,
      data_sensitivity: dataSensitivity || undefined,
      insurance_coverage: insuranceCoverage || undefined,
    };
  }

  async function runReview() {
    const hasFileInput = !!selectedFile;
    const hasTextInput = text.trim().length > 0;
    const canRun = inputMode === "file" ? hasFileInput : hasTextInput;

    if (!canRun) return;

    setLoading(true);
    resetResultState();
    setErrorMessage(null);

    try {
      const requestInit =
        inputMode === "file" && selectedFile
          ? (() => {
              const formData = new FormData();
              formData.append("file", selectedFile, selectedFile.name);
              Object.entries(contextPayload()).forEach(([key, value]) => {
                if (value) formData.append(key, String(value));
              });
              return { method: "POST", body: formData };
            })()
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                text,
                source_title:
                  reportTitle.trim() ||
                  DOCUMENT_TYPE_OPTIONS.find((option) => option.value === documentType)?.label ||
                  undefined,
                source_type: "text",
                ...contextPayload(),
                value_criticality: reviewPurpose.toLowerCase().includes("renewal") ? "recurring" : undefined,
                document_position: reviewPurpose.toLowerCase().includes("renewal") ? "renewal" : undefined,
              }),
            };

      const response = await fetch("/api/analyze", requestInit);
      const raw = await response.text();

      if (!response.ok) {
        const detail = extractCustomerError(raw);
        setErrorMessage(
          response.status === 401
            ? "Sign in is required to use the VoxaRisk dashboard."
            : `Analysis could not be completed. ${detail}`,
        );
        return;
      }

      const data: AnalyzeResult = JSON.parse(raw);
      setResult(data);
      setReportGeneratedAt(new Date().toISOString());
      setScanDecision({ state: "pending" });
      setFindingDecisions({});
      setDecisionMessage(null);
      const history = await loadScanHistory();
      const latestScan = history?.scans?.[0];
      if (latestScan?.id) {
        setActiveScanId(latestScan.id);
        setScanDecision(latestScan.decision_state ?? { state: "pending" });
      }
    } catch (error) {
      setErrorMessage(
        `Analysis could not be completed at this time. Review the source text or file and try again. ${String(error)}`,
      );
    } finally {
        setLoading(false);
    }
  }

  async function generateAIReviewNotes() {
    if (!result) return;

    if (!accountContext?.entitlement.ai_review_notes_allowed) {
      setAIReview(null);
      setAIState("denied");
      setAIMessage("AI explanation is available on eligible plans.");
      return;
    }

    setAIState("loading");
    setAIMessage(null);

    try {
      const response = await fetch("/api/ai/explain", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(buildAIExplainPayload(result)),
      });

      const payload = (await response.json().catch(() => null)) as AIExplainResponse | { detail?: unknown } | null;

      if (response.status === 403) {
        setAIReview(null);
        setAIState("denied");
        setAIMessage("AI explanation is available on eligible plans.");
        return;
      }

      if (!response.ok) {
        setAIReview(null);
        setAIState("unavailable");
        setAIMessage(
          "AI explanation could not be generated. Core VoxaRisk analysis remains complete.",
        );
        return;
      }

      const aiPayload = normalizeAIExplainResponse(payload as AIExplainResponse | null);

      if (aiPayload?.status === "available" && aiPayload.ai_summary) {
        setAIReview(aiPayload as NormalizedAIExplainResponse);
        setAIState("available");
        return;
      }

      setAIReview(null);
      setAIState(aiPayload?.status === "disabled" ? "disabled" : "unavailable");
      setAIMessage(
        "AI explanation could not be generated. Core VoxaRisk analysis remains complete.",
      );
    } catch {
      setAIReview(null);
      setAIState("unavailable");
      setAIMessage(
        "AI explanation could not be generated. Core VoxaRisk analysis remains complete.",
      );
    }
  }

  async function updateScanDecision(nextState: ScanDecisionValue, note?: string) {
    if (!activeScanId) {
      setDecisionMessage("Decision controls become available once the review is saved or reopened from history.");
      return;
    }

    setDecisionSavingKey("scan");
    setDecisionMessage(null);
    try {
      const response = await fetch(`/api/account/scans/${encodeURIComponent(activeScanId)}/decision`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: nextState, note }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        setDecisionMessage("Scan decision could not be saved. The review remains available.");
        return;
      }
      const nextDecision = payload?.decision_state ?? { state: nextState, note, updated_at: new Date().toISOString() };
      setScanDecision(nextDecision);
      setDecisionMessage("Scan decision saved.");
      void loadScanHistory();
    } catch {
      setDecisionMessage("Scan decision could not be saved. The review remains available.");
    } finally {
      setDecisionSavingKey(null);
    }
  }

  async function updateFindingDecision(findingId: string, nextStatus: FindingDecisionValue, note?: string) {
    if (!activeScanId) {
      setDecisionMessage("Finding decisions become available once the review is saved or reopened from history.");
      return;
    }

    setDecisionSavingKey(findingId);
    setDecisionMessage(null);
    try {
      const response = await fetch(
        `/api/account/scans/${encodeURIComponent(activeScanId)}/findings/${encodeURIComponent(findingId)}/decision`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: nextStatus, note }),
        },
      );
      const payload = await response.json().catch(() => null);
      if (!response.ok) {
        setDecisionMessage("Finding decision could not be saved. The analysis remains visible.");
        return;
      }
      const nextDecision = payload?.finding_decision ?? {
        finding_id: findingId,
        status: nextStatus,
        note,
        updated_at: new Date().toISOString(),
      };
      setFindingDecisions((current) => ({ ...current, [findingId]: nextDecision }));
      setDecisionMessage("Finding decision saved.");
      void loadScanHistory();
    } catch {
      setDecisionMessage("Finding decision could not be saved. The analysis remains visible.");
    } finally {
      setDecisionSavingKey(null);
    }
  }

  const normalizedScore = result
    ? result.meta?.normalized_score ?? exposureScoreFromStoredRiskScore(result.risk_score)
    : 0;
  const aiReviewSections = useMemo(() => formatAIReviewSections(aiReview?.ai_summary), [aiReview?.ai_summary]);
  const findings = useMemo(() => result?.findings ?? [], [result?.findings]);
  const topRisks = useMemo(() => result?.meta?.top_risks ?? [], [result?.meta?.top_risks]);
  const confidence = result?.meta?.confidence ?? 0;
  const matchedRuleCount = result?.meta?.matched_rule_count ?? findings.length;
  const wordCount = result?.meta?.word_count ?? 0;
  const hasTextInput = text.trim().length > 0;
  const hasFileInput = !!selectedFile;
  const hasInput = inputMode === "file" ? hasFileInput : hasTextInput;
  const uploadedBaseName = selectedFile ? stripExtension(selectedFile.name) : "";
  const reportTitleFallback = reportTitle.trim() || uploadedBaseName || documentType || "Contract Risk Report";
  const reportVisibleTitle = reportTitle.trim() || reportTitleFallback;
  const reportTitleSlug = sanitizeFilenameSegment(reportTitleFallback) || "Contract_Risk_Report";
  const reportDateSlug = new Date().toISOString().slice(0, 10);
  const reportFilename = `VoxaRisk_${reportTitleSlug}_Risk_Report_${reportDateSlug}.pdf`;
  const summaryCategories = useMemo(
    () => [
      ...topRisks.map((risk) => risk.category ?? ""),
      ...findings.map((finding) => finding.category ?? ""),
    ],
    [topRisks, findings],
  );
  const primaryCategory = useMemo(
    () => topRisks[0]?.category ?? findings[0]?.category ?? "",
    [topRisks, findings],
  );
  const leadFinding = useMemo(() => findings[0] ?? null, [findings]);
  const leadRuleId = useMemo(
    () => topRisks[0]?.rule_id ?? findings[0]?.rule_id ?? "",
    [topRisks, findings],
  );
  const posture = useMemo(() => {
    if (!result) return null;
    const backendPosture = backendDecisionPosture(result);
    if (backendPosture) return backendPosture;
    return decisionPosture(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);
  const policyTrace = useMemo(() => result?.meta?.policy_trace ?? [], [result?.meta?.policy_trace]);
  const intelligenceSnapshot = result?.meta?.decision_intelligence ?? null;
  const contractMemory = result?.meta?.contract_memory ?? intelligenceSnapshot?.contract_memory ?? null;
  const negotiationIntel = result?.meta?.negotiation_intelligence ?? intelligenceSnapshot?.negotiation_intelligence ?? null;
  const sectorJurisdictionIntel =
    result?.meta?.sector_jurisdiction_intelligence ?? intelligenceSnapshot?.sector_jurisdiction_intelligence ?? null;
  const linkedDocumentIntel =
    result?.meta?.linked_document_intelligence ?? intelligenceSnapshot?.linked_document_intelligence ?? null;
  const findingGroups = useMemo(() => {
    const groups: Record<"Critical" | "High" | "Moderate" | "Low", Finding[]> = {
      Critical: [],
      High: [],
      Moderate: [],
      Low: [],
    };
    findings.forEach((finding) => {
      groups[findingImpactGroup(finding)].push(finding);
    });
    return groups;
  }, [findings]);
  const elevatedFindings = useMemo(
    () => [...findingGroups.Critical, ...findingGroups.High, ...findingGroups.Moderate],
    [findingGroups],
  );
  const policyUnknownCount = useMemo(
    () => findings.filter((finding) => finding.policy_status === "policy_unknown").length,
    [findings],
  );
  const unresolvedFindingCount = useMemo(
    () =>
      findings.filter((finding, index) => {
        const decision = findingDecisions[findingDecisionId(finding, index)];
        return !decision || !decision.status || decision.status === "unresolved";
      }).length,
    [findings, findingDecisions],
  );
  const synthesisSignals = useMemo(() => {
    const raw = [
      ...(result?.meta?.synthesis_patterns_triggered ?? []),
      ...(linkedDocumentIntel?.conflict_signals?.map((item) => item.type ?? "linked_document_conflict") ?? []),
      ...(sectorJurisdictionIntel?.notes?.map((item) => item.signal ?? "") ?? []),
    ].filter(Boolean);
    return Array.from(new Set(raw.map((item) => synthesisLabel(String(item))))).slice(0, 6);
  }, [result?.meta?.synthesis_patterns_triggered, linkedDocumentIntel?.conflict_signals, sectorJurisdictionIntel?.notes]);
  const primarySummary = useMemo(() => {
    if (!result) return "";
    return executiveSummary(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);
  const isLowSignalResult = (topRisks.length === 0 && findings.length === 0 && result?.severity === "LOW") || false;
  const effectiveConfidence =
    typeof confidence === "number" && confidence > 0
      ? confidence
      : typeof result?.confidence_hint === "number"
        ? result.confidence_hint
        : null;
  const baseReliabilityAssessment = reviewReliability(effectiveConfidence);
  const reliabilityAssessment = isLowSignalResult
    ? {
        label: "Low signal" as ReliabilityLabel,
        helper: result?.meta?.reliability_wording ?? "Extraction completed; no covered rule signal detected.",
      }
    : baseReliabilityAssessment;
  const decisionPrimaryRiskType = isLowSignalResult
    ? result?.meta?.primary_risk_type ?? "No elevated rule signal"
    : decisionPrimaryRiskTypeLabel(primaryCategory);
  const decisionImpactArea = isLowSignalResult ? "Automated triage coverage" : decisionImpactAreaLabel(primaryCategory);
  const decisionConfidenceDriver = isLowSignalResult
    ? result?.meta?.confidence_driver ?? "No governed rule match detected in reviewed text"
    : decisionConfidenceDriverLabel(
        leadRuleId,
        reliabilityAssessment.label,
        leadFinding?.matched_location,
      );
  const decisionSignalType = isLowSignalResult
    ? result?.meta?.signal_type ?? "Low-signal automated review"
    : "Structural clause-level exposure";
  const reportGeneratedLabel = formatReportTimestamp(reportGeneratedAt);
  const reportPriorityItems = (topRisks.length ? topRisks : findings).slice(0, 3);
  const negotiationPriorityCount = negotiationIntel?.priorities?.length ?? reportPriorityItems.length;
  const duplicatedSummaryDetail =
    !isLowSignalResult &&
    primarySummary.trim().length > 0 &&
    primarySummary.trim() === (posture?.detail ?? "").trim();
  const executiveSummaryDetail = isLowSignalResult
    ? "Final acceptance should still consider commercial dependency, deal context, and professional review where appropriate."
    : duplicatedSummaryDetail
      ? ""
      : posture?.detail ?? "";
  const decisionSnapshotSeverity = result
    ? `${severityTone(result.severity === "HIGH" ? 4 : result.severity === "MEDIUM" ? 3 : 1)} severity`
    : "Not stated";
  const reviewRecordItems = [
    { label: "Generated", value: reportGeneratedLabel },
    {
      label: "Format",
      value: readableSourceType(result?.source_type ?? (inputMode === "file" ? "file" : "text")),
    },
    { label: "Capture method", value: readableExtractionMethod(result?.extraction_method ?? "direct review") },
    {
      label: "Approx. word count",
      value: wordCount ? String(wordCount) : "Not stated",
    },
    {
      label: "Internal reference",
      value: internalReference.trim() || "Not provided",
    },
  ];
  const canUseAI = accountContext?.entitlement.ai_review_notes_allowed ?? false;
  const reportBoundaryNotice =
    "VoxaRisk provides commercial risk decision support. It does not provide legal advice, legal opinion, contract approval, compliance certification or universal jurisdiction outcomes. Users remain responsible for commercial and legal decisions and should obtain professional advice where appropriate.";

  function handlePrintReport() {
    if (!result) {
      setErrorMessage("Run a contract risk review first to generate a report.");
      return;
    }

    if (!reportTitle.trim()) {
      setReportValidationMessage("Add a concise report title or reference before generating the executive report.");
      return;
    }

    setReportValidationMessage(null);
    previousTitleRef.current = document.title;
    document.title = reportFilename.replace(/\.pdf$/i, "");
    window.print();
    window.setTimeout(() => {
      if (previousTitleRef.current !== null) {
        document.title = previousTitleRef.current;
        previousTitleRef.current = null;
      }
    }, 1200);
  }

  if (authState === "loading") {
    return (
      <>
        <main className="min-h-screen bg-[#F5F1EB] text-neutral-950">
          <SiteHeader className="report-print-hidden" />
          <div className="mx-auto max-w-4xl px-6 py-16 md:px-8">
            <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-10 text-center shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                Dashboard access
              </div>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-neutral-950">
                Confirming account access
              </h1>
              <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-neutral-700">
                VoxaRisk is checking the current account session before loading the contract review workspace.
              </p>
            </div>
          </div>
        </main>
        <div className="report-print-hidden">
          <SiteFooter />
        </div>
      </>
    );
  }

  if (authState === "unauthenticated") {
    return (
      <>
        <main className="min-h-screen bg-[#F5F1EB] text-neutral-950">
          <SiteHeader className="report-print-hidden" authMode="unauthenticated" emphasizeSignIn />
          <div className="mx-auto max-w-4xl px-6 py-16 md:px-8">
            <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-10 text-center shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                Dashboard access
              </div>
              <h1 className="mt-3 text-3xl font-semibold tracking-tight text-neutral-950">
                Sign in to open the VoxaRisk review workspace
              </h1>
              <p className="mx-auto mt-4 max-w-2xl text-sm leading-7 text-neutral-700">
                Contract risk review, decision records, executive reporting, and export are available only inside a signed-in VoxaRisk account workspace.
              </p>
              <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
                <Link
                  href="/signin"
                  className="rounded-2xl bg-[#1E1712] px-6 py-3 text-sm font-semibold text-[#EDE7DF] transition hover:bg-[#241C16]"
                >
                  Sign in
                </Link>
                <Link
                  href="/pricing"
                  className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] px-6 py-3 text-sm font-semibold text-[#6f552d] transition hover:bg-[#efe4d0]"
                >
                  View plans
                </Link>
              </div>
            </div>
          </div>
        </main>
        <div className="report-print-hidden">
          <SiteFooter />
        </div>
      </>
    );
  }

  return (
    <>
      <main className="min-h-screen bg-[#F5F1EB] text-neutral-950">
        <SiteHeader className="report-print-hidden" activeItem="dashboard" authMode="authenticated" />

        <div className="mx-auto max-w-[1500px] px-5 py-6 md:px-8">
          {result && (
            <section className="report-print-hidden mb-5 rounded-[30px] border border-[#d2bd96] bg-[#1E1712] p-5 text-[#EDE7DF] shadow-[0_20px_48px_rgba(30,23,18,0.18)] md:p-6">
              <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_220px_260px] xl:items-center">
                <div className="min-w-0">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#c8a96d]">
                    Executive decision signal
                  </div>
                  <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[#F5F1EB] md:text-4xl">
                    {posture?.label ?? "Review required"}
                  </h1>
                  <p className="mt-3 max-w-4xl text-sm leading-6 text-[#d8cec2]">
                    {posture?.nextStep ?? primarySummary}
                  </p>
                </div>
                <div className="rounded-2xl border border-[rgba(216,190,142,0.28)] bg-[#2A211B] p-4">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[#c8a96d]">Exposure</div>
                  <div className="mt-1 flex items-end gap-2">
                    <span className="text-5xl font-semibold leading-none">{normalizedScore}</span>
                    <span className="pb-1 text-xs uppercase tracking-[0.14em] text-[#c8a96d]">{result.severity}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#c8a96d]">Top drivers</div>
                    <div className="mt-1 text-2xl font-semibold">{elevatedFindings.length || findings.length}</div>
                  </div>
                  <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-3">
                    <div className="text-[10px] uppercase tracking-[0.16em] text-[#c8a96d]">Negotiation</div>
                    <div className="mt-1 text-2xl font-semibold">{negotiationPriorityCount}</div>
                  </div>
                </div>
              </div>
            </section>
          )}

          <div className="report-print-hidden mb-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_260px] xl:grid-cols-[minmax(0,1fr)_280px]">
            <section className="overflow-hidden rounded-[28px] border border-[rgba(180,150,90,0.22)] bg-[#241C16] text-[#EDE7DF] shadow-[0_16px_34px_rgba(36,28,22,0.14)]">
              <div className="border-b border-[rgba(180,150,90,0.18)] bg-[#1E1712] px-4 py-3 md:px-5">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">
                  Decision Workspace
                </div>
                <div className="mt-2 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                  <div>
                    <h1 className="text-xl font-semibold tracking-tight text-[#EDE7DF] md:text-2xl">
                      Contract risk decision console
                    </h1>
                    <p className="mt-2 max-w-2xl text-sm leading-6 text-[#cfc4b8]">
                      Paste or upload the contract. The decision signal appears above the workspace after review.
                    </p>
                  </div>
                  <div className="text-xs font-medium uppercase tracking-[0.18em] text-[#a98c5a]">
                    Signed-in workspace
                  </div>
                </div>
              </div>

              <div className="grid gap-3 p-3 md:p-4 xl:grid-cols-[1.05fr_0.95fr]">
                <section className="rounded-2xl border border-[rgba(180,150,90,0.18)] bg-[#2A211B] p-3">
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[rgba(180,150,90,0.2)] pb-3">
                    <div>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d5bd88]">
                        Contract Input
                      </div>
                      <p className="mt-1 text-xs leading-5 text-[#bfb3a7]">
                        Paste text or upload a file for governed review.
                      </p>
                    </div>
                    <div className="text-xs text-[#a98c5a]">
                      {inputMode === "file" ? uploadLabel : `${text.trim().length} characters`}
                    </div>
                  </div>

                  <div className="mt-4 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setInputMode("text")}
                      className={`border px-3 py-2 text-xs font-semibold transition ${
                        inputMode === "text"
                          ? "border-[#d5bd88] bg-[#322720] text-[#EDE7DF]"
                          : "border-[rgba(180,150,90,0.2)] bg-[#241C16] text-[#cfc4b8] hover:border-[#b08d57]"
                      }`}
                    >
                      Paste text
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setInputMode("file");
                        fileInputRef.current?.click();
                      }}
                      className={`border px-3 py-2 text-xs font-semibold transition ${
                        inputMode === "file"
                          ? "border-[#d5bd88] bg-[#322720] text-[#EDE7DF]"
                          : "border-[rgba(180,150,90,0.2)] bg-[#241C16] text-[#cfc4b8] hover:border-[#b08d57]"
                      }`}
                    >
                      Upload PDF / Image
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setInputMode("file");
                        cameraInputRef.current?.click();
                      }}
                      className="border border-[rgba(180,150,90,0.2)] bg-[#241C16] px-3 py-2 text-xs font-semibold text-[#cfc4b8] transition hover:border-[#b08d57]"
                    >
                      Use camera
                    </button>
                    {selectedFile && (
                      <button
                        type="button"
                        onClick={clearUpload}
                        className="border border-[rgba(180,150,90,0.2)] bg-[#241C16] px-3 py-2 text-xs font-semibold text-[#cfc4b8] transition hover:border-[#b08d57]"
                      >
                        Clear file
                      </button>
                    )}
                  </div>

                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,image/jpeg,image/jpg,image/png,image/webp"
                    className="hidden"
                    onChange={onFileInputChange}
                  />

                  <input
                    ref={cameraInputRef}
                    type="file"
                    accept="image/*"
                    capture="environment"
                    className="hidden"
                    onChange={onFileInputChange}
                  />

                  <div className="mt-4 border border-dashed border-[rgba(180,150,90,0.26)] bg-[#241C16] p-3">
                    <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#d5bd88]">
                      Intake mode
                    </div>
                    <div className="mt-1 text-xs leading-5 text-[#cfc4b8]">
                      {inputMode === "file"
                        ? `File mode active. ${uploadLabel}`
                        : "Text mode active. Paste the contract or clauses for commercial risk review."}
                    </div>
                  </div>

                  <textarea
                    value={text}
                    onChange={(event) => {
                      setText(event.target.value);
                      if (event.target.value.trim()) {
                        setInputMode("text");
                        setSelectedFile(null);
                        setUploadLabel("No file selected");
                        if (fileInputRef.current) fileInputRef.current.value = "";
                        if (cameraInputRef.current) cameraInputRef.current.value = "";
                      }
                    }}
                    placeholder="Paste key clauses or full contract text here..."
                    className="mt-3 min-h-[118px] w-full rounded-2xl border border-[rgba(180,150,90,0.2)] bg-[#1E1712] px-4 py-3 text-sm leading-6 text-[#EDE7DF] outline-none transition placeholder:text-[#8f8174] focus:border-[#b08d57]"
                  />

                  {errorMessage && (
                    <div className="mt-3 border border-red-300/30 bg-red-950/20 p-3 text-sm leading-6 text-red-100">
                      {errorMessage}
                    </div>
                  )}

                  <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <div className="text-xs leading-5 text-[#a98c5a]">
                      Core scoring is rules-first. AI notes are secondary explanation only.
                    </div>
                    <button
                      onClick={runReview}
                      disabled={loading || !hasInput}
                      className="rounded-2xl bg-[#d5bd88] px-5 py-3 text-sm font-semibold text-[#1E1712] shadow-[0_10px_20px_rgba(0,0,0,0.13)] transition hover:bg-[#e1c998] disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {loading ? "Reviewing..." : "Run Executive Review"}
                    </button>
                  </div>
                </section>

                <div className="grid gap-4">
                  <section className="rounded-2xl border border-[rgba(180,150,90,0.18)] bg-[#2A211B] p-3">
                    <div className="flex items-center justify-between gap-3 border-b border-[rgba(180,150,90,0.2)] pb-3">
                      <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d5bd88]">
                        Detected Signals
                      </div>
                      <div className="text-xs text-[#a98c5a]">
                        {result ? `${matchedRuleCount} findings` : "Awaiting scan"}
                      </div>
                    </div>
                    <div className="mt-3 space-y-2">
                      {result && (reportPriorityItems.length || findings.length) ? (
                        (reportPriorityItems.length ? reportPriorityItems : findings).slice(0, 4).map((item, index) => (
                          <div key={`workspace-signal-${item.title ?? "risk"}-${index}`} className="flex items-center justify-between gap-3 border-b border-[rgba(180,150,90,0.14)] py-2 last:border-b-0">
                            <span className="min-w-0 truncate text-sm text-[#EDE7DF]">{item.title ?? "Unlabeled risk"}</span>
                            <span className="shrink-0 text-xs uppercase tracking-[0.14em] text-[#a98c5a]">{item.category ?? "risk"}</span>
                          </div>
                        ))
                      ) : (
                        <div className="text-sm leading-6 text-[#cfc4b8]">
                          Run a review to populate governed clause signals and evidence-linked risk drivers.
                        </div>
                      )}
                    </div>
                  </section>

                  <section className="rounded-2xl border border-[rgba(180,150,90,0.18)] bg-[#2A211B] p-3">
                    <div className="border-b border-[rgba(180,150,90,0.2)] pb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d5bd88]">
                      Risk Score
                    </div>
                    <div className="mt-4 flex items-end justify-between gap-4">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#a98c5a]">
                          {result ? `${result.severity} exposure` : "Not calculated"}
                        </div>
                        <div className="mt-2 text-5xl font-semibold leading-none text-[#EDE7DF]">
                          {result ? normalizedScore : "--"}
                        </div>
                      </div>
                      <div className="h-16 w-px bg-[#b08d57]/55" />
                      <div className="max-w-[150px] text-xs leading-5 text-[#cfc4b8]">
                        {result ? scoreBand(normalizedScore, result.severity) : "Exposure score appears after analysis."}
                      </div>
                    </div>
                  </section>

                  <section className="rounded-2xl border border-[#d5bd88]/35 bg-[#2A211B] p-3 shadow-[0_0_18px_rgba(176,141,87,0.08)]">
                    <div className="border-b border-[rgba(180,150,90,0.24)] pb-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d5bd88]">
                      Decision Output
                    </div>
                    <div className="mt-3 text-xl font-semibold uppercase leading-tight text-[#EDE7DF] md:text-2xl">
                      {posture?.label ?? "Awaiting Review"}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-[#cfc4b8]">
                      {posture?.nextStep ?? "Run a scan to generate hold, accept, escalate, or renegotiate guidance."}
                    </p>
                  </section>
                </div>
              </div>
            </section>

            <aside className="border border-[rgba(180,150,90,0.2)] bg-[#2A211B] p-4 text-[#EDE7DF] shadow-[0_18px_42px_rgba(36,28,22,0.14)] lg:sticky lg:top-6 lg:self-start">
              <div className="border-b border-[rgba(180,150,90,0.2)] pb-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#d5bd88]">
                  Workspace Context
                </div>
                <div className="mt-1 text-xs leading-5 text-[#bfb3a7]">
                  Account and entitlement state for this review session.
                </div>
              </div>

              <dl className="mt-4 space-y-3 text-sm">
                {[
                  { label: "Organisation", value: accountContext?.organization.name ?? "Workspace" },
                  { label: "Plan", value: accountContext?.entitlement.effective_plan ?? "starter" },
                  { label: "Monthly limit", value: `${accountContext?.entitlement.monthly_scan_limit ?? 0} reviews` },
                  { label: "Session", value: "Active" },
                ].map((item) => (
                  <div key={item.label} className="flex items-start justify-between gap-4 border-b border-[rgba(180,150,90,0.14)] pb-3 last:border-b-0 last:pb-0">
                    <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#a98c5a]">{item.label}</dt>
                    <dd className="min-w-0 text-right font-semibold capitalize text-[#EDE7DF]">{item.value}</dd>
                  </div>
                ))}
              </dl>

              <div className="mt-4 border border-[rgba(180,150,90,0.18)] bg-[#241C16] p-3 text-xs leading-5 text-[#cfc4b8]" title={accountContext?.user.email ?? "Account verified"}>
                Session verified for the signed-in workspace.
              </div>
            </aside>
          </div>

          {result && (
            <>
              <div className="report-print-hidden">
                <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px] xl:items-start">
                  <div className="min-w-0 space-y-6">
                    <section className="rounded-[26px] border border-[#d2bd96] bg-[#fffdf8] p-5 shadow-[0_10px_22px_rgba(80,60,30,0.05)] md:p-6">
                      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                            Executive Summary
                          </div>
                          <h2 className="mt-2 max-w-4xl text-2xl font-semibold tracking-tight text-neutral-950 md:text-3xl">
                            {scoreBand(normalizedScore, result.severity)} exposure · {posture?.label ?? "Review required"}
                          </h2>
                          <p className="mt-3 max-w-4xl text-sm leading-6 text-neutral-700 md:text-[0.95rem]">
                            {primarySummary}
                          </p>
                        </div>
                        <div className={`shrink-0 rounded-full border px-4 py-2 text-sm font-semibold ${severityBadgeClass(result.severity)}`}>
                          {result.severity}
                        </div>
                      </div>

                      <div className="mt-4 grid gap-3 md:grid-cols-4">
                        {[
                          { label: "Exposure", value: normalizedScore },
                          { label: "Top drivers", value: elevatedFindings.length || findings.length },
                          { label: "Negotiation", value: negotiationPriorityCount },
                          { label: "Reliability", value: reliabilityAssessment.label },
                        ].map((item) => (
                          <div key={item.label} className="min-h-[76px] rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-3">
                            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">{item.label}</div>
                            <div className="mt-2 truncate text-2xl font-semibold text-neutral-950" title={String(item.value)}>
                              {item.value}
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="mt-5 grid gap-3 md:grid-cols-3">
                        <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Primary risk</div>
                          <div className="mt-2 text-sm font-semibold leading-5 text-neutral-950">{decisionPrimaryRiskType}</div>
                        </div>
                        <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Impact area</div>
                          <div className="mt-2 text-sm font-semibold leading-5 text-neutral-950">{decisionImpactArea}</div>
                        </div>
                        <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Signal</div>
                          <div className="mt-2 text-sm font-semibold leading-5 text-neutral-950">{decisionSignalType}</div>
                        </div>
                      </div>
                      <div className="mt-3 rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Confidence driver</div>
                        <div className="mt-2 text-sm leading-6 text-neutral-700">{decisionConfidenceDriver}</div>
                      </div>
                    </section>

                    <section className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_minmax(280px,0.72fr)]">
                      <div className="rounded-[28px] border border-[#dccaa8] bg-[#fffaf0] p-5 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                              Top Risk Drivers
                            </div>
                            <h3 className="mt-2 text-xl font-semibold text-neutral-950">What deserves attention first</h3>
                          </div>
                        </div>
                        <div className="mt-3 grid gap-3">
                          {reportPriorityItems.length ? (
                            reportPriorityItems.map((item, index) => {
                              const category = item.category ?? "";
                              return (
                                <article key={`priority-${item.title ?? "risk"}-${index}`} className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                                  <div className="flex gap-3">
                                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[#b08d57] bg-[#fffaf0] text-sm font-semibold text-[#6f552d]">
                                      {index + 1}
                                    </div>
                                    <div className="min-w-0">
                                      <h4 className="text-sm font-semibold leading-5 text-neutral-950">{item.title ?? "Unlabeled risk"}</h4>
                                      <p className="mt-1 max-h-12 overflow-hidden text-sm leading-6 text-neutral-700">
                                        {priorityReason(category)}
                                      </p>
                                    </div>
                                  </div>
                                </article>
                              );
                            })
                          ) : (
                            <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4 text-sm leading-6 text-[#8f7245]">
                              No elevated driver was detected by the governed rules. Continue normal review for off-text dependencies.
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="rounded-[28px] border border-[#dccaa8] bg-[#fffdf8] p-5 shadow-[0_12px_28px_rgba(80,60,30,0.05)]">
                        <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                          Negotiation Priorities
                        </div>
                        <h3 className="mt-2 text-xl font-semibold text-neutral-950">Bounded preparation</h3>
                        <div className="mt-4 space-y-3">
                          {(negotiationIntel?.priorities?.length ? negotiationIntel.priorities.slice(0, 3) : []).map((item, index) => (
                            <div key={`${item.title ?? "negotiation"}-${index}`} className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                              <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8f7245]">{item.priority ?? "Priority"}</div>
                              <div className="mt-1 text-sm font-semibold leading-5 text-neutral-950">{item.title ?? "Negotiation issue"}</div>
                              <p className="mt-2 max-h-12 overflow-hidden text-sm leading-6 text-neutral-700">
                                {item.clause_revision_objectives?.[0] ?? negotiationIntel?.minimum_acceptable_controls?.[0] ?? "Review the deterministic priority before acceptance."}
                              </p>
                            </div>
                          ))}
                          {!negotiationIntel?.priorities?.length && (
                            <p className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4 text-sm leading-6 text-neutral-700">
                              No negotiation demand is elevated from the current deterministic result.
                            </p>
                          )}
                        </div>
                      </div>
                    </section>

                    <section className="rounded-[28px] border border-[#dccaa8] bg-[#fffaf0] p-5 shadow-[0_12px_28px_rgba(80,60,30,0.05)]">
                      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                        <div>
                          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                            Cross-Signal Intelligence
                          </div>
                          <h3 className="mt-2 text-xl font-semibold text-neutral-950">Combined patterns, not repeated findings</h3>
                        </div>
                        <div className="text-xs leading-5 text-[#8f7245]">Deterministic synthesis only</div>
                      </div>
                      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                        {(synthesisSignals.length ? synthesisSignals : ["No compound pattern elevated"]).map((signal) => (
                          <div key={signal} className="rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-4">
                            <div className="text-sm font-semibold text-neutral-950">{signal}</div>
                            <p className="mt-2 max-h-12 overflow-hidden text-xs leading-5 text-neutral-600">
                              {signal === "No compound pattern elevated"
                                ? "Current findings do not create a separately elevated synthesis pattern."
                                : "Review the linked top drivers and evidence before deciding whether to accept, negotiate, or escalate."}
                            </p>
                          </div>
                        ))}
                      </div>
                      {(policyUnknownCount > 0 || unresolvedFindingCount > 0) && (
                        <div className="mt-4 rounded-2xl border border-[#e6d8bd] bg-[#fffcf6] p-3 text-xs leading-5 text-[#8f7245]">
                          Governance note: {policyUnknownCount} finding{policyUnknownCount === 1 ? "" : "s"} without configured policy and {unresolvedFindingCount} unresolved finding-level decision{unresolvedFindingCount === 1 ? "" : "s"}. Shown once here to avoid repeated metadata noise.
                        </div>
                      )}
                      {(contractMemory?.recurring_counterparty?.detected || contractMemory?.recurring_risky_clauses?.length || policyTrace.length > 0) && (
                        <div className="mt-3 grid gap-3 md:grid-cols-2">
                          {contractMemory?.recurring_counterparty?.detected && (
                            <div className="rounded-2xl border border-[#e6d8bd] bg-[#fffcf6] p-3">
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Contract memory</div>
                              <p className="mt-1 text-xs leading-5 text-neutral-700">
                                Recurring counterparty signal across {contractMemory.recurring_counterparty.prior_scan_count ?? 0} prior review{contractMemory.recurring_counterparty.prior_scan_count === 1 ? "" : "s"} in this workspace.
                              </p>
                            </div>
                          )}
                          {Boolean(contractMemory?.recurring_risky_clauses?.length) && (
                            <div className="rounded-2xl border border-[#e6d8bd] bg-[#fffcf6] p-3">
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Repeated exposure</div>
                              <p className="mt-1 text-xs leading-5 text-neutral-700">
                                {contractMemory?.recurring_risky_clauses?.slice(0, 2).map((item) => item.family).filter(Boolean).join(", ")} recurring clause family signal{(contractMemory?.recurring_risky_clauses?.length ?? 0) === 1 ? "" : "s"}.
                              </p>
                            </div>
                          )}
                          {policyTrace.length > 0 && (
                            <div className="rounded-2xl border border-[#e6d8bd] bg-[#fffcf6] p-3 md:col-span-2">
                              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Policy signal</div>
                              <p className="mt-1 text-xs leading-5 text-neutral-700">
                                {policyTrace.length} policy tolerance check{policyTrace.length === 1 ? "" : "s"} evaluated for this review. Material conflicts remain attached to the relevant finding.
                              </p>
                            </div>
                          )}
                        </div>
                      )}
                    </section>

                    <section className="rounded-[26px] border border-[#dccaa8] bg-[#fffaf0] p-5 shadow-[0_10px_22px_rgba(80,60,30,0.05)] md:p-6">
                      <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
                        <div>
                          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#8f7245]">
                            Condensed Findings
                          </div>
                          <h3 className="mt-2 text-xl font-semibold text-neutral-950">Grouped by impact</h3>
                        </div>
                        <div className="text-xs leading-5 text-[#8f7245]">Open a finding for evidence and decision controls.</div>
                      </div>

                      <div className="mt-5 space-y-4">
                        {(["Critical", "High", "Moderate", "Low"] as const).map((groupName) => {
                          const group = findingGroups[groupName];
                          if (!group.length) return null;
                          const tone = groupFindingTone(groupName);
                          const visible = groupName === "Low" ? group.slice(0, 3) : group.slice(0, 6);
                          const hidden = group.slice(visible.length);

                          const renderFinding = (finding: Finding, index: number) => {
                            const originalIndex = findings.indexOf(finding);
                            const findingId = findingDecisionId(finding, originalIndex >= 0 ? originalIndex : index);
                            const decision = findingDecisions[findingId] ?? { finding_id: findingId, status: "unresolved" };
                            const policy = policyIndicator(finding);
                            const noteOpen = Boolean(decisionNotesOpen[findingId]);
                            const noteDraft = findingDecisionNotes[findingId] ?? decision.note ?? "";
                            const showPolicy = policy && finding.policy_status !== "policy_unknown";
                            const roleAwareSections = [
                              { label: "Structural", value: finding.structural_risk ?? finding.role_aware_interpretation?.["Structural Risk"] },
                              { label: "Context", value: finding.contextual_impact ?? finding.role_aware_interpretation?.["Contextual Impact"] },
                              { label: "Operational", value: finding.operational_exposure ?? finding.role_aware_interpretation?.["Operational Exposure"] },
                              { label: "Attention", value: finding.recommended_attention ?? finding.role_aware_interpretation?.["Recommended Attention"] },
                            ].filter((section) => section.value);

                            return (
                              <article key={`${findingId}-${index}`} className={`rounded-2xl border p-3 ${tone.wrapper}`}>
                                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                                  <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className={`h-2 w-2 rounded-full ${tone.dot}`} />
                                      <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                                        {finding.category ?? "uncategorized"}
                                      </span>
                                    </div>
                                    <h4 className="mt-2 text-base font-semibold leading-6 text-neutral-950">{finding.title ?? "Unlabeled finding"}</h4>
                                    <p className="mt-2 max-h-[3.2rem] overflow-hidden text-sm leading-5 text-neutral-700">
                                      {finding.rationale ?? consequenceSummary(finding.category)}
                                    </p>
                                  </div>
                                  <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-semibold ${tone.badge}`}>
                                    {severityTone(finding.severity)}
                                  </span>
                                </div>

                                {finding.matched_text && (
                                  <div className="mt-2 rounded-xl border border-[#e3d4bb] bg-[#fffdf8] p-3">
                                    <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">Evidence preview</div>
                                    <p className="mt-1 max-h-16 overflow-hidden break-words text-xs leading-5 text-neutral-600">
                                      {finding.matched_text}
                                    </p>
                                  </div>
                                )}

                                <details className="mt-2 rounded-xl border border-[#e3d4bb] bg-[#fffdf8] p-3">
                                  <summary className="cursor-pointer text-sm font-semibold text-neutral-950">Evidence, controls, and decision record</summary>
                                  <div className="mt-3 space-y-3">
                                    {showPolicy && (
                                      <div className={`rounded-xl border p-3 text-xs leading-5 ${policy.className}`}>
                                        <span className="font-semibold">{policy.label}:</span> {policy.detail}
                                      </div>
                                    )}
                                    {roleAwareSections.length > 0 && (
                                      <div className="grid gap-2 md:grid-cols-2">
                                        {roleAwareSections.map((section) => (
                                          <div key={section.label} className="rounded-xl border border-[#e3d4bb] bg-[#fffcf6] p-3">
                                            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-[#8f7245]">{section.label}</div>
                                            <p className="mt-1 text-xs leading-5 text-neutral-700">{section.value}</p>
                                          </div>
                                        ))}
                                      </div>
                                    )}
                                    {finding.matched_text && (
                                      <div className="max-h-56 overflow-y-auto rounded-xl border border-[#dccaa8] bg-[#fffaf0] p-3 text-sm leading-6 text-neutral-700">
                                        {finding.matched_text}
                                      </div>
                                    )}
                                    <div>
                                      <div className="mb-2 flex flex-wrap gap-2">
                                        {acceptableGuidance(finding).slice(0, 4).map((item) => (
                                          <span key={item} className="rounded-full border border-[#dccaa8] bg-[#fcf2df] px-3 py-1 text-xs font-medium text-[#6f552d]">
                                            {item}
                                          </span>
                                        ))}
                                      </div>
                                      <div className="flex flex-wrap items-center gap-2">
                                        <span className="rounded-full border border-[#e3d4bb] bg-[#fffcf6] px-3 py-1 text-xs font-semibold text-[#765a2b]">
                                          {findingDecisionLabel(decision.status)}
                                        </span>
                                        <select
                                          value={(decision.status as FindingDecisionValue) || "unresolved"}
                                          onChange={(event) => void updateFindingDecision(findingId, event.target.value as FindingDecisionValue, noteDraft)}
                                          disabled={!activeScanId || decisionSavingKey === findingId}
                                          className="rounded-xl border border-[#dccaa8] bg-[#fffdf8] px-3 py-2 text-sm text-neutral-800 disabled:opacity-60"
                                        >
                                          {FINDING_DECISION_OPTIONS.map((option) => (
                                            <option key={option.value} value={option.value}>{option.label}</option>
                                          ))}
                                        </select>
                                        <button
                                          type="button"
                                          onClick={() => setDecisionNotesOpen((current) => ({ ...current, [findingId]: !noteOpen }))}
                                          className="text-xs font-semibold text-[#765a2b] underline-offset-4 hover:underline"
                                        >
                                          {noteOpen ? "Hide note" : decision.note ? "Edit note" : "Add note"}
                                        </button>
                                      </div>
                                      {noteOpen && (
                                        <div className="mt-2">
                                          <textarea
                                            value={noteDraft}
                                            onChange={(event) => setFindingDecisionNotes((current) => ({ ...current, [findingId]: event.target.value }))}
                                            rows={3}
                                            placeholder="Add a short commercial rationale or exception note."
                                            className="w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-3 text-sm leading-6 text-neutral-800 outline-none focus:border-[#b08d57]"
                                          />
                                          <button
                                            type="button"
                                            onClick={() => void updateFindingDecision(findingId, (decision.status as FindingDecisionValue) || "unresolved", noteDraft)}
                                            disabled={!activeScanId || decisionSavingKey === findingId}
                                            className="mt-2 rounded-full bg-[#1E1712] px-4 py-2 text-xs font-semibold text-[#EDE7DF] transition hover:bg-[#241C16] disabled:cursor-not-allowed disabled:opacity-60"
                                          >
                                            Save note
                                          </button>
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </details>
                              </article>
                            );
                          };

                          return (
                            <details key={groupName} open={groupName !== "Low"} className="rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-4">
                              <summary className="cursor-pointer list-none">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                  <div className="flex items-center gap-3">
                                    <span className={`h-2.5 w-2.5 rounded-full ${tone.dot}`} />
                                    <div>
                                      <div className="text-sm font-semibold text-neutral-950">{groupName} findings</div>
                                      <div className="text-xs text-[#8f7245]">{group.length} item{group.length === 1 ? "" : "s"}</div>
                                    </div>
                                  </div>
                                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${tone.badge}`}>Open / close</span>
                                </div>
                              </summary>
                              <div className="mt-4 space-y-3">
                                {visible.map(renderFinding)}
                                {hidden.length > 0 && (
                                  <details className="rounded-2xl border border-[#e3d4bb] bg-[#fffcf6] p-3">
                                    <summary className="cursor-pointer text-sm font-semibold text-neutral-950">
                                      Show {hidden.length} more {groupName.toLowerCase()} finding{hidden.length === 1 ? "" : "s"}
                                    </summary>
                                    <div className="mt-3 space-y-3">{hidden.map(renderFinding)}</div>
                                  </details>
                                )}
                              </div>
                            </details>
                          );
                        })}
                        {!findings.length && (
                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5 text-sm leading-6 text-[#8f7245]">
                            No detailed clause-level findings were elevated. This remains a low-signal automated result, not contract approval.
                          </div>
                        )}
                      </div>
                    </section>

                    <section className="rounded-[24px] border border-[#e0cfad] bg-[#fbf6ed] p-4 shadow-[0_8px_18px_rgba(80,60,30,0.035)] md:p-5">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                          AI Review Notes
                        </div>
                        <h3 className="mt-2 text-xl font-semibold text-neutral-950">
                          Secondary explanation layer
                        </h3>
                        <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
                          Generated from deterministic findings and clause evidence. AI does not change the score, severity, findings, or decision posture.
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={generateAIReviewNotes}
                        disabled={aiState === "loading" || !canUseAI}
                        className="rounded-2xl border border-[#cdb78d] bg-[#fffaf0] px-5 py-3 text-sm font-semibold text-neutral-900 transition hover:bg-[#f3e4c6] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {aiState === "loading"
                          ? "Generating evidence-grounded AI notes..."
                          : canUseAI
                            ? "Generate AI Review Notes"
                            : "AI explanation available on eligible plans"}
                      </button>
                    </div>

                    {(!canUseAI ||
                      aiState === "disabled" ||
                      aiState === "unavailable" ||
                      aiState === "denied" ||
                      aiState === "error") && (
                        aiMessage || !canUseAI
                      ) && (
                        <div className="mt-6 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4 text-sm leading-6 text-neutral-700">
                          {aiMessage ?? "AI explanation is available on eligible plans."}
                        </div>
                      )}

                    {aiState === "available" && aiReview?.ai_summary && aiReviewSections.length > 0 && (
                      <div className="mt-6 rounded-[28px] border border-[#d4bd94] bg-[#fffaf0] p-5 shadow-[0_14px_32px_rgba(80,60,30,0.07)] md:p-6">
                        <div className="flex flex-col gap-2 border-b border-[#e3d4bb] pb-4 md:flex-row md:items-end md:justify-between">
                          <div>
                            <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                              AI Review
                            </div>
                            <h4 className="mt-2 text-xl font-semibold tracking-tight text-neutral-950">
                              Executive briefing note
                            </h4>
                          </div>
                          <div className="text-xs font-medium text-[#8f7245]">
                            Explanation layer only
                          </div>
                        </div>

                        <div className="mt-5 space-y-4">
                          {aiReviewSections
                            .filter((section) => section.kind !== "boundary")
                            .map((section) => (
                              <section
                                key={section.heading}
                                className="border-l-2 border-[#b08d57]/50 bg-[#fcf7ee] px-4 py-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
                              >
                                <div className="text-[0.68rem] font-semibold uppercase tracking-[0.22em] text-[#8f7245]">
                                  {section.heading}
                                </div>
                                {section.kind === "paragraph" ? (
                                  <div className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                                    {section.items.map((item) => (
                                      <p key={item} className="max-w-4xl">
                                        {renderAITextWithEmphasis(item)}
                                      </p>
                                    ))}
                                  </div>
                                ) : (
                                  <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                                    {section.items.map((item) => (
                                      <li key={item} className="flex gap-3">
                                        <span className="mt-[0.6rem] h-1.5 w-1.5 shrink-0 rounded-full bg-[#8f7245]" />
                                        <span>{renderAITextWithEmphasis(item)}</span>
                                      </li>
                                    ))}
                                  </ul>
                                )}
                              </section>
                            ))}
                        </div>

                        {aiReviewSections
                          .filter((section) => section.kind === "boundary")
                          .slice(0, 1)
                          .map((section) => (
                            <div key={section.heading} className="mt-5 border-t border-[#e3d4bb] pt-4 text-xs leading-5 text-[#8f7245]">
                              {section.items[0]}
                            </div>
                          ))}
                      </div>
                    )}
                    </section>
                  </div>

                  <aside className="top-5 rounded-[26px] border border-[#d2bd96] bg-[#1E1712] p-4 text-[#EDE7DF] shadow-[0_14px_32px_rgba(30,23,18,0.16)] xl:sticky">
                    <div className="text-xs font-semibold uppercase tracking-[0.24em] text-[#c8a96d]">Executive Rail</div>
                    <div className="mt-3 grid gap-3">
                      <div className="rounded-2xl border border-[rgba(216,190,142,0.24)] bg-[#2a211a] p-3">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-[#c8a96d]">Exposure score</div>
                        <div className="mt-1 text-4xl font-semibold">{normalizedScore}</div>
                        <div className="mt-1 text-xs text-[#bfb3a7]">{result.severity} · {reliabilityAssessment.label}</div>
                      </div>
                      <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-4">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-[#c8a96d]">Posture</div>
                        <div className="mt-2 text-lg font-semibold leading-6">{posture?.label ?? "Review required"}</div>
                      </div>
                      <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-4">
                        <div className="text-[11px] uppercase tracking-[0.18em] text-[#c8a96d]">Next action</div>
                        <p className="mt-2 max-h-24 overflow-hidden text-sm leading-6 text-[#d8cec2]">{posture?.nextStep ?? "Review the top drivers before recording the commercial decision."}</p>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-3">
                          <div className="text-[10px] uppercase tracking-[0.16em] text-[#c8a96d]">Priorities</div>
                          <div className="mt-1 text-2xl font-semibold">{negotiationPriorityCount}</div>
                        </div>
                        <div className="rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-3">
                          <div className="text-[10px] uppercase tracking-[0.16em] text-[#c8a96d]">Unresolved</div>
                          <div className="mt-1 text-2xl font-semibold">{unresolvedFindingCount}</div>
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 rounded-2xl border border-[rgba(216,190,142,0.22)] bg-[#241C16] p-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-[11px] uppercase tracking-[0.18em] text-[#c8a96d]">Scan decision</div>
                          <div className="mt-1 text-sm font-semibold">{scanDecisionLabel(scanDecision.state)}</div>
                        </div>
                      </div>
                      <select
                        value={(scanDecision.state as ScanDecisionValue) || "pending"}
                        onChange={(event) => void updateScanDecision(event.target.value as ScanDecisionValue)}
                        disabled={!activeScanId || decisionSavingKey === "scan"}
                        className="mt-3 w-full rounded-xl border border-[rgba(216,190,142,0.32)] bg-[#1E1712] px-3 py-2 text-sm text-[#EDE7DF] disabled:opacity-60"
                      >
                        {SCAN_DECISION_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>{option.label}</option>
                        ))}
                      </select>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {[
                          { label: "Accept", value: "accepted" as ScanDecisionValue },
                          { label: "Escalate", value: "escalated" as ScanDecisionValue },
                          { label: "Legal", value: "sent_for_legal_review" as ScanDecisionValue },
                        ].map((action) => (
                          <button
                            key={action.value}
                            type="button"
                            onClick={() => void updateScanDecision(action.value)}
                            disabled={!activeScanId || decisionSavingKey === "scan"}
                            className="rounded-full border border-[rgba(216,190,142,0.38)] bg-[#332820] px-3 py-1.5 text-xs font-semibold text-[#EDE7DF] transition hover:bg-[#3c3027] disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>
                    </div>

                    {decisionMessage && (
                      <div className="mt-3 rounded-2xl border border-[rgba(216,190,142,0.24)] bg-[#241C16] p-3 text-xs leading-5 text-[#d8cec2]">
                        {decisionMessage}
                      </div>
                    )}

                    <details className="mt-4 rounded-2xl border border-[rgba(216,190,142,0.18)] bg-[#241C16] p-3">
                      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.18em] text-[#c8a96d]">Boundary</summary>
                      <p className="mt-2 text-xs leading-5 text-[#bfb3a7]">{reportBoundaryNotice}</p>
                    </details>
                  </aside>
                </div>
              </div>

              <section className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)] md:p-8">
                <div
                  data-report-root
                  className="report-surface mx-auto max-w-[920px] rounded-[24px] border border-[#dccaa8] bg-[#fffaf0] px-6 py-6 md:px-8 md:py-7"
                >
                  <header className="report-section border-b border-[#dccaa8] pb-4">
                    <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
                      <div className="flex gap-4">
                        <img
                          src="/brand/voxa-circle-logo.png"
                          alt="VoxaRisk"
                          className="h-14 w-14 rounded-full border border-[#dccaa8] object-cover"
                        />
                        <div>
                          <div className="text-sm font-semibold uppercase tracking-[0.28em] text-[#8f7245]">
                            VoxaRisk
                          </div>
                          <h3 className="mt-2 text-[1.85rem] font-semibold tracking-tight text-neutral-950">
                            {reportVisibleTitle}
                          </h3>
                          <p className="mt-1.5 text-sm font-medium text-[#8f7245]">
                            Contract Risk Intelligence Report
                          </p>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] px-4 py-2.5 text-sm text-neutral-700">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.2em] text-[#8f7245]">
                          Generated
                        </div>
                        <div className="mt-1.5 font-semibold text-neutral-950">{reportGeneratedLabel}</div>
                      </div>
                    </div>

                    <div className="mt-4 border-y border-[#e6d8bd] bg-[#fcf6eb] px-4 py-3">
                      <div className="grid gap-x-5 gap-y-2 text-sm md:grid-cols-2 xl:grid-cols-4">
                        <div className="flex min-w-0 items-baseline gap-2">
                          <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                            Reliability:
                          </span>
                          <span className="truncate font-semibold text-neutral-950" title={reliabilityAssessment.helper}>
                            {reliabilityAssessment.label}
                          </span>
                        </div>
                        <div className="flex min-w-0 items-baseline gap-2">
                          <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                            Prepared for:
                          </span>
                          <span className="truncate font-semibold text-neutral-950">
                            {preparedFor.trim() || "Not specified"}
                          </span>
                        </div>
                        <div className="flex min-w-0 items-baseline gap-2">
                          <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                            Document type:
                          </span>
                          <span className="truncate font-semibold text-neutral-950">
                            {documentType || "Not specified"}
                          </span>
                        </div>
                        <div className="flex min-w-0 items-baseline gap-2">
                          <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                            Review purpose:
                          </span>
                          <span className="truncate font-semibold text-neutral-950">
                            {reviewPurpose || "Not specified"}
                          </span>
                        </div>
                      </div>
                    </div>
                  </header>

                  <section className="report-section mt-5 border-b border-[#e6d8bd] pb-5">
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                      Executive Summary
                    </div>
                    <h4 className="mt-2 text-[1.65rem] font-semibold tracking-tight text-neutral-950">
                      {posture?.label ?? "Review required"}
                    </h4>
                    <div className="mt-3 space-y-3 text-sm leading-6 text-neutral-700">
                      <p>
                        {topRisks.length || findings.length || result.severity !== "LOW"
                          ? primarySummary
                          : lowSignalSummary()}
                      </p>
                      {executiveSummaryDetail ? <p>{executiveSummaryDetail}</p> : null}
                    </div>
                  </section>

                  <section className="report-section mt-5 border-b border-[#e6d8bd] pb-5">
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                      Decision Snapshot
                    </div>
                    <div className="mt-4 grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2 xl:grid-cols-3">
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Posture:
                        </span>
                        <span className="font-semibold text-neutral-950">
                          {posture?.label ?? "Review required"}
                        </span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Signal:
                        </span>
                        <span className="font-semibold text-neutral-950">
                          {scoreBand(normalizedScore, result.severity)} exposure
                        </span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Severity:
                        </span>
                        <span className="font-semibold text-neutral-950">{decisionSnapshotSeverity}</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Exposure score:
                        </span>
                        <span className="font-semibold text-neutral-950">{normalizedScore}</span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Reliability:
                        </span>
                        <span className="font-semibold text-neutral-950" title={reliabilityAssessment.helper}>
                          {reliabilityAssessment.label}
                        </span>
                      </div>
                      <div className="flex items-baseline gap-2">
                        <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Detected findings:
                        </span>
                        <span className="font-semibold text-neutral-950">{matchedRuleCount}</span>
                      </div>
                    </div>
                  </section>

                  <section className="report-section mt-5 border-b border-[#e6d8bd] pb-5">
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                      Primary Risk Drivers
                    </div>
                    {reportPriorityItems.length ? (
                      <div className="mt-4 space-y-3">
                        {reportPriorityItems.map((item, index) => {
                          const category = item.category ?? "";
                          return (
                            <div key={`report-priority-${item.title ?? "risk"}-${index}`} className="space-y-1.5">
                              <div className="text-base font-semibold text-neutral-950">
                                {`Priority ${index + 1}: ${item.title ?? "Unlabeled risk"}`}
                              </div>
                              <p className="text-sm leading-6 text-neutral-700">
                                {negotiationPriority(category)}
                              </p>
                              <p className="text-sm leading-6 text-neutral-700">{priorityReason(category)}</p>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm leading-6 text-neutral-700">
                        No material automated risk signals were elevated into negotiation priorities. This remains a low-signal automated result, not contract approval.
                      </p>
                    )}
                  </section>

                  <section className="report-section mt-5 border-b border-[#e6d8bd] pb-5">
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                      Findings
                    </div>
                    {findings.length ? (
                      <div className="mt-4 space-y-4">
                        {findings.map((finding, index) => (
                          <article key={`${finding.rule_id ?? "report-finding"}-${index}`} className="space-y-2">
                            <div className="flex flex-col gap-1.5 md:flex-row md:items-baseline md:justify-between">
                              <h5 className="text-base font-semibold text-neutral-950">
                                {finding.title ?? "Unlabeled finding"}
                              </h5>
                              <div className="text-xs font-medium uppercase tracking-[0.18em] text-[#8f7245]">
                                {(finding.category ?? "uncategorized") + " · " + severityTone(finding.severity) + " impact"}
                              </div>
                            </div>
                            <p className="text-sm leading-6 text-neutral-700">
                              {finding.rationale ?? consequenceSummary(finding.category)}
                            </p>
                            <p className="text-sm leading-6 text-neutral-700">
                              <span className="font-semibold text-neutral-950">Recommended focus:</span>{" "}
                              {recommendedFocus(finding.category)}
                            </p>
                            {finding.matched_text && (
                              <p className="border-l-2 border-[#d8c29b] pl-4 text-sm leading-6 text-neutral-700">
                                <span className="font-semibold text-neutral-950">Clause evidence:</span>{" "}
                                {finding.matched_text}
                              </p>
                            )}
                          </article>
                        ))}
                      </div>
                    ) : (
                      <p className="mt-3 text-sm leading-6 text-neutral-700">
                        No detailed clause-level findings were elevated in this review.
                      </p>
                    )}
                  </section>

                  <section className="report-section mt-5">
                    <div className="grid gap-5 lg:grid-cols-[1.05fr_0.95fr]">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                          Review Record
                        </div>
                        <div className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                          {reviewRecordItems.map((item) => (
                            <div key={item.label} className="flex gap-2">
                              <span className="shrink-0 font-semibold text-neutral-950">{item.label}:</span>
                              <span>{item.value}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                          Boundary
                        </div>
                        <p className="mt-3 text-sm leading-6 text-neutral-700">
                          {reportBoundaryNotice}
                        </p>
                      </div>
                    </div>
                  </section>
                </div>
              </section>

              <section className="report-print-hidden rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)] md:p-8">
                <div className="border-t border-[#dccaa8] pt-6">
                  <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                    Prepare Executive Report
                  </div>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-950">
                    Prepare Executive Report
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-700">
                    Add a concise reference so the exported report is titled, filed, and presented professionally.
                  </p>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-[#8f7245]">
                    Use a short contract or matter reference and avoid unnecessary personal data.
                  </p>

                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Report title / reference
                      </span>
                      <input
                        value={reportTitle}
                        onChange={(event) => setReportTitle(event.target.value.slice(0, 100))}
                        placeholder="HSBC Supplier Agreement Review"
                        maxLength={100}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Prepared for
                      </span>
                      <input
                        value={preparedFor}
                        onChange={(event) => setPreparedFor(event.target.value.slice(0, 80))}
                        placeholder="Board Review"
                        maxLength={80}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Document type
                      </span>
                      <select
                        value={documentType}
                        onChange={(event) => setDocumentType(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select document type</option>
                        {DOCUMENT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Review purpose
                      </span>
                      <select
                        value={reviewPurpose}
                        onChange={(event) => setReviewPurpose(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select review purpose</option>
                        {REVIEW_PURPOSE_OPTIONS.map((option) => (
                          <option key={option} value={option}>
                            {option}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Your position
                      </span>
                      <select
                        value={contextUserRole}
                        onChange={(event) => setContextUserRole(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select role</option>
                        {CONTEXT_ROLE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Criticality
                      </span>
                      <select
                        value={criticalityLevel}
                        onChange={(event) => setCriticalityLevel(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select criticality</option>
                        {CRITICALITY_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Risk posture
                      </span>
                      <select
                        value={riskPosture}
                        onChange={(event) => setRiskPosture(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        {RISK_POSTURE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Deal value
                      </span>
                      <input
                        value={dealValue}
                        onChange={(event) => setDealValue(event.target.value.slice(0, 80))}
                        placeholder="e.g. 250000"
                        maxLength={80}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Industry
                      </span>
                      <input
                        value={industry}
                        onChange={(event) => setIndustry(event.target.value.slice(0, 80))}
                        placeholder="Fintech, healthcare, procurement"
                        maxLength={80}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Jurisdiction
                      </span>
                      <input
                        value={jurisdiction}
                        onChange={(event) => setJurisdiction(event.target.value.slice(0, 80))}
                        placeholder="UK, EU, US"
                        maxLength={80}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Data sensitivity
                      </span>
                      <select
                        value={dataSensitivity}
                        onChange={(event) => setDataSensitivity(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select sensitivity</option>
                        {DATA_SENSITIVITY_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block">
                      <span className="text-sm font-semibold text-neutral-900">
                        Insurance coverage
                      </span>
                      <select
                        value={insuranceCoverage}
                        onChange={(event) => setInsuranceCoverage(event.target.value)}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      >
                        <option value="">Select coverage</option>
                        {INSURANCE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </label>

                    <label className="block md:col-span-2">
                      <span className="text-sm font-semibold text-neutral-900">
                        Internal reference
                      </span>
                      <input
                        value={internalReference}
                        onChange={(event) => setInternalReference(event.target.value.slice(0, 50))}
                        placeholder="VR-2026-0041"
                        maxLength={50}
                        className="mt-2 w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-3 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
                      />
                    </label>
                  </div>

                  {reportValidationMessage && (
                    <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
                      {reportValidationMessage}
                    </div>
                  )}

                  <div className="mt-6 flex flex-col gap-3">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                      <div className="text-sm text-[#8f7245]">
                        Export filename: {reportFilename}
                      </div>
                      <button
                        type="button"
                        onClick={handlePrintReport}
                        className="rounded-2xl bg-[#1E1712] px-5 py-3 text-sm font-medium text-[#EDE7DF] transition hover:opacity-90"
                      >
                        Generate Executive Report
                      </button>
                    </div>
                    <div className="text-xs text-neutral-500">
                      For a clean PDF, use Save as PDF where available and turn off browser Headers and footers in the print dialog.
                    </div>
                  </div>
                </div>
              </section>
            </>
          )}

          <section className="report-print-hidden mt-6 border border-[#dccaa8] bg-[#eee6d8] p-4 shadow-[0_10px_24px_rgba(80,60,30,0.04)] md:p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8f7245]">
                  Previous Reviews
                </div>
                <h2 className="mt-1 text-lg font-semibold text-[#1E1712]">Recent workspace history</h2>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void loadScanHistory()}
                  className="border border-[#dccaa8] bg-[#f8f2e8] px-3 py-2 text-xs font-semibold text-[#6f552d]"
                >
                  Refresh
                </button>
                <Link href="/account/scans" className="border border-[#b08d57] bg-[#f8f2e8] px-3 py-2 text-xs font-semibold text-[#6f552d]">
                  View full history →
                </Link>
              </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_240px]">
              <div className="grid gap-3 md:grid-cols-3">
                {historyLoading && (
                  <div className="border border-[#dccaa8] bg-[#f8f2e8] p-3 text-sm text-neutral-600 md:col-span-3">
                    Loading review history...
                  </div>
                )}
                {!historyLoading && scanHistory.length === 0 && (
                  <div className="border border-[#dccaa8] bg-[#f8f2e8] p-3 text-sm text-neutral-600 md:col-span-3">
                    No previous contract risk reviews stored for this organisation yet.
                  </div>
                )}
                {scanHistory.slice(0, 3).map((scan) => {
                  const severity =
                    scan.severity === "HIGH" || scan.severity === "MEDIUM" || scan.severity === "LOW"
                      ? scan.severity
                      : "LOW";
                  const exposureScore = scanHistoryExposureScore(scan);
                  const displayTitle = scanHistoryDisplayTitle(scan, severity);
                  return (
                    <button
                      key={scan.id}
                      type="button"
                      onClick={() => void reopenStoredScan(scan.id)}
                      className="min-w-0 border border-[#dccaa8] bg-[#f8f2e8] p-3 text-left opacity-90 transition hover:border-[#b08d57] hover:opacity-100"
                    >
                      <div className="truncate text-sm font-semibold text-[#1E1712]">{displayTitle}</div>
                      <div className="mt-1 text-xs text-[#8f7245]">
                        {formatReportTimestamp(scan.created_at)} · {readableSourceType(scan.source_type)}
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <span className={`border px-2 py-1 text-[11px] font-semibold ${severityBadgeClass(severity)}`}>
                          {severity}
                        </span>
                        <span className="border border-[#dccaa8] bg-[#eee6d8] px-2 py-1 text-[11px] text-[#6f552d]">
                          {exposureScore === null ? "Exposure unavailable" : `Exposure ${exposureScore}`}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              <aside className="border border-[#dccaa8] bg-[#f8f2e8] p-3">
                <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Recurring families
                </div>
                <div className="mt-3 space-y-2 text-xs text-neutral-700">
                  {recurringFamilies.slice(0, 4).map((item) => (
                    <div key={item.family} className="flex items-center justify-between gap-3">
                      <span className="truncate">{item.family}</span>
                      <span className="font-semibold text-[#1E1712]">{item.count}</span>
                    </div>
                  ))}
                  {recurringFamilies.length === 0 && <div>No recurring families yet.</div>}
                </div>
              </aside>
            </div>
          </section>
        </div>
      </main>

      <div className="report-print-hidden">
        <SiteFooter />
      </div>

      <style jsx global>{`
        @page {
          size: A4;
          margin: 12mm;
        }

        @media print {
          html,
          body {
            background: #ffffff !important;
          }

          .report-print-hidden {
            display: none !important;
          }

          body * {
            visibility: hidden;
          }

          [data-report-root],
          [data-report-root] * {
            visibility: visible;
          }

          [data-report-root] {
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
            max-width: none !important;
            margin: 0 !important;
            border: none !important;
            box-shadow: none !important;
            border-radius: 0 !important;
            padding: 0 !important;
            background: #ffffff !important;
          }

          .report-section,
          .report-card,
          .report-findings article {
            break-inside: avoid-page;
            page-break-inside: avoid;
          }

          .report-page-break {
            break-before: auto;
            page-break-before: auto;
          }
        }
      `}</style>
    </>
  );
}
