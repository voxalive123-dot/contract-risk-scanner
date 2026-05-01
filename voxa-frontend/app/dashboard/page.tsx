"use client";

import Link from "next/link";
import { ChangeEvent, useEffect, useMemo, useRef, useState } from "react";

import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

type ScoreAdjustment = {
  type?: string;
  effect?: number;
  reason?: string;
};

type Finding = {
  rule_id?: string;
  title?: string;
  category?: string;
  severity?: number;
  rationale?: string;
  matched_text?: string;
  matched_location?: string | null;
  context_note?: string | null;
  contextual_emphasis?: string | null;
  policy_category?: string | null;
  policy_value?: string | null;
  policy_status?: string | null;
  policy_explanation?: string | null;
  decision_guidance?: string[];
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
  };
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
  reason?: string;
  ai_summary?: AIReviewSummary;
  summary?: AIReviewSummary;
  ai_review?: AIReviewSummary;
  review_notes?: AIReviewSummary;
  data?: {
    ai_summary?: AIReviewSummary;
    summary?: AIReviewSummary;
  };
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
  "Supplier Agreement",
  "NDA",
  "Service Agreement",
  "Loan Agreement",
  "Lease",
  "Employment Contract",
  "Other",
] as const;

const REVIEW_PURPOSE_OPTIONS = [
  "Pre-signature review",
  "Negotiation preparation",
  "Renewal review",
  "Internal risk screen",
  "Supplier onboarding",
] as const;

function severityTone(severity?: number) {
  if ((severity ?? 0) >= 4) return "High";
  if ((severity ?? 0) >= 3) return "Moderate";
  return "Low";
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
) {
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
    label: "Proceed with Standard Review",
    detail:
      "No material automated risk signal was elevated in the reviewed text. This should be treated as a low-signal automated result, not as contract approval.",
    nextStep:
      "Final acceptance should still consider commercial dependency, deal context, and professional review where appropriate.",
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

type ReliabilityLabel = "Strong" | "Moderate" | "Limited";

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

function buildAIExplainPayload(result: AnalyzeResult) {
  return {
    risk_score: result.risk_score,
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
  return value.charAt(0).toUpperCase() + value.slice(1);
}

function readableExtractionMethod(value?: string | null) {
  if (!value) return "Direct review";
  return value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());
}

function extractCustomerError(raw: string) {
  try {
    const parsed = JSON.parse(raw);
    if (typeof parsed?.error === "string") return parsed.error;
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (typeof parsed?.detail?.error === "string") return parsed.detail.error;
  } catch {
    return raw;
  }
  return raw;
}

function normalizeAIExplainResponse(payload: AIExplainResponse | null): AIExplainResponse | null {
  if (!payload) return null;

  const summary =
    payload.ai_summary ??
    payload.summary ??
    payload.ai_review ??
    payload.review_notes ??
    payload.data?.ai_summary ??
    payload.data?.summary;

  const directSummary =
    !summary && (payload.overview || payload.risk_posture_summary)
      ? {
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
  };
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
  const [internalReference, setInternalReference] = useState("");
  const [reportValidationMessage, setReportValidationMessage] = useState<string | null>(null);
  const [aiReview, setAIReview] = useState<AIExplainResponse | null>(null);
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
      setResult({
        risk_score: detail.risk_score,
        severity,
        flags: detail.clause_families_detected ?? [],
        findings: detail.top_findings ?? [],
        meta: {
          confidence: detail.confidence ?? 0,
          matched_rule_count: detail.top_findings?.length ?? 0,
          top_risks: detail.top_findings ?? [],
          rule_families_detected: detail.clause_families_detected ?? [],
          synthesis_patterns_triggered: detail.synthesis_patterns_triggered ?? [],
          context_profile_used: detail.context_profile_snapshot ?? null,
        },
        source_type: detail.source_type ?? "unknown",
      });
      setReportGeneratedAt(detail.created_at ?? new Date().toISOString());
      setReportTitle(detail.source_title ?? "Stored contract risk review");
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
              return { method: "POST", body: formData };
            })()
          : {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                text,
                source_title: reportTitle.trim() || documentType || undefined,
                source_type: "text",
                user_role: undefined,
                contract_type: documentType.toLowerCase().includes("service") ? "services" : undefined,
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
        setAIReview(aiPayload);
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

  const normalizedScore = result?.meta?.normalized_score ?? result?.risk_score ?? 0;
  const rawRiskScore = result?.risk_score ?? 0;
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
    return decisionPosture(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);
  const primarySummary = useMemo(() => {
    if (!result) return "";
    return executiveSummary(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);
  const effectiveConfidence =
    typeof confidence === "number" && confidence > 0
      ? confidence
      : typeof result?.confidence_hint === "number"
        ? result.confidence_hint
        : null;
  const reliabilityAssessment = reviewReliability(effectiveConfidence);
  const decisionPrimaryRiskType = decisionPrimaryRiskTypeLabel(primaryCategory);
  const decisionImpactArea = decisionImpactAreaLabel(primaryCategory);
  const decisionConfidenceDriver = decisionConfidenceDriverLabel(
    leadRuleId,
    reliabilityAssessment.label,
    leadFinding?.matched_location,
  );
  const reportGeneratedLabel = formatReportTimestamp(reportGeneratedAt);
  const reportPriorityItems = (topRisks.length ? topRisks : findings).slice(0, 3);
  const isLowSignalResult = (topRisks.length === 0 && findings.length === 0 && result?.severity === "LOW") || false;
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
        <main className="min-h-screen bg-[linear-gradient(180deg,#f7f3ea_0%,#f1e5cf_100%)] text-neutral-950">
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
        <main className="min-h-screen bg-[linear-gradient(180deg,#f7f3ea_0%,#f1e5cf_100%)] text-neutral-950">
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
                  className="rounded-2xl bg-[#11110f] px-6 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1a1a17]"
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
      <main className="min-h-screen bg-[linear-gradient(180deg,#f7f3ea_0%,#f1e5cf_100%)] text-neutral-950">
        <SiteHeader className="report-print-hidden" activeItem="dashboard" authMode="authenticated" />

        <div className="mx-auto max-w-7xl px-6 py-8 md:px-8">
          <div className="report-print-hidden mb-8 grid gap-5 rounded-3xl border border-[#dccaa8] bg-[#fffaf0] px-6 py-5 shadow-[0_12px_28px_rgba(80,60,30,0.06)] lg:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.95fr)] lg:px-7">
            <div className="min-w-0">
              <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                Contract Risk Decision Workspace
              </div>
              <h1 className="mt-2.5 text-[2rem] font-semibold tracking-tight text-neutral-950">
                Decision intelligence console
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-neutral-700">
                Paste contract text or upload a document to generate structured risk intelligence, tolerance-aware review posture, negotiation focus, and an executive record.
              </p>
            </div>

            <aside className="rounded-[1.35rem] border border-[#d2bd96] bg-[#fcf2df] p-5 shadow-[0_10px_22px_rgba(80,60,30,0.05)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8f7245]">
                Workspace
              </div>

              <dl className="mt-4 grid grid-cols-[minmax(0,1fr)_auto] gap-x-5 gap-y-2.5 text-sm">
                <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Organisation
                </dt>
                <dd className="min-w-0 text-right font-semibold text-neutral-950">
                  {accountContext?.organization.name ?? "Workspace"}
                </dd>

                <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Plan
                </dt>
                <dd className="text-right font-semibold capitalize text-neutral-950">
                  {accountContext?.entitlement.effective_plan ?? "starter"}
                </dd>

                <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Monthly limit
                </dt>
                <dd className="text-right font-semibold text-neutral-950">
                  {(accountContext?.entitlement.monthly_scan_limit ?? 0) + " reviews"}
                </dd>

                <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Session
                </dt>
                <dd className="text-right font-semibold text-neutral-950">
                  Active
                </dd>
              </dl>

              <div
                className="mt-4 text-xs leading-5 text-neutral-500"
                title={accountContext?.user.email ?? "Account verified"}
              >
                Account verified
              </div>
            </aside>
          </div>


          <div className="report-print-hidden mb-8 rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-neutral-950">Previous reviews</h2>
                <p className="mt-1 text-sm text-[#8f7245]">
                  Organisation-scoped review history for this workspace. Stored snapshots keep evidence, recurring risk families, and decision context visible without cross-customer analytics.
                </p>
              </div>
              <button
                type="button"
                onClick={() => void loadScanHistory()}
                className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] px-4 py-2 text-sm font-medium text-neutral-700"
              >
                Refresh
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
              <div className="space-y-3">
                {historyLoading && (
                  <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4 text-sm text-neutral-600">
                    Loading review history...
                  </div>
                )}
                {!historyLoading && scanHistory.length === 0 && (
                  <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4 text-sm text-neutral-600">
                    No previous contract risk reviews stored for this organisation yet.
                  </div>
                )}
                {scanHistory.slice(0, 5).map((scan) => {
                  const severity =
                    scan.severity === "HIGH" || scan.severity === "MEDIUM" || scan.severity === "LOW"
                      ? scan.severity
                      : "LOW";
                  return (
                    <button
                      key={scan.id}
                      type="button"
                      onClick={() => void reopenStoredScan(scan.id)}
                      className="w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-4 text-left transition hover:border-[#b08d57]"
                    >
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="truncate text-sm font-semibold text-neutral-950">
                            {scan.source_title || "Untitled scan"}
                          </div>
                          <div className="mt-1 text-xs text-[#8f7245]">
                            {scan.created_at ? new Date(scan.created_at).toLocaleDateString() : "Date unavailable"} · {readableSourceType(scan.source_type)}
                          </div>
                        </div>
                        <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${severityBadgeClass(severity)}`}>
                          {severity} · {scan.risk_score}
                        </span>
                      </div>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {(scan.clause_families_detected ?? []).slice(0, 4).map((family) => (
                          <span key={family} className="rounded-full border border-[#dccaa8] bg-[#fcf2df] px-2.5 py-1 text-xs text-[#6f552d]">
                            {family}
                          </span>
                        ))}
                        <span className="rounded-full border border-[#dccaa8] bg-[#fcf2df] px-2.5 py-1 text-xs text-[#6f552d]">
                          report: {scan.report_export_state ?? "absent"}
                        </span>
                      </div>
                    </button>
                  );
                })}
              </div>

              <aside className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                  Recurring families
                </div>
                <div className="mt-3 space-y-2 text-sm text-neutral-700">
                  {recurringFamilies.slice(0, 6).map((item) => (
                    <div key={item.family} className="flex items-center justify-between gap-3">
                      <span>{item.family}</span>
                      <span className="font-semibold text-neutral-950">{item.count}</span>
                    </div>
                  ))}
                  {recurringFamilies.length === 0 && <div>No recurring families yet.</div>}
                </div>
              </aside>
            </div>
          </div>

          <div className="report-print-hidden mb-8 rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-neutral-950">Contract input</h2>
                <p className="mt-1 text-sm text-[#8f7245]">
                  Paste contract text or upload a supported file for decision-ready commercial review.
                </p>
              </div>
              <div className="text-xs text-neutral-500">Signed-in workspace only</div>
            </div>

            <div className="mb-4 flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setInputMode("text")}
                className={`rounded-2xl border px-4 py-2 text-sm font-medium ${
                  inputMode === "text"
                    ? "border-[#11110f] bg-[#11110f] text-stone-100"
                    : "border-[#dccaa8] bg-[#fffaf0] text-neutral-700"
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
                className={`rounded-2xl border px-4 py-2 text-sm font-medium ${
                  inputMode === "file"
                    ? "border-[#11110f] bg-[#11110f] text-stone-100"
                    : "border-[#dccaa8] bg-[#fffaf0] text-neutral-700"
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
                className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] px-4 py-2 text-sm font-medium text-neutral-700"
              >
                Use camera
              </button>
              {selectedFile && (
                <button
                  type="button"
                  onClick={clearUpload}
                  className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] px-4 py-2 text-sm font-medium text-neutral-700"
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

            <div className="mb-4 rounded-2xl border border-dashed border-[#d6c4a0] bg-[#fcf2df] p-4">
              <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                Intake mode
              </div>
              <div className="mt-2 text-sm text-neutral-700">
                {inputMode === "file"
                  ? `File mode active. ${uploadLabel}`
                  : "Text mode active. Paste the contract or the clauses that need commercial risk review."}
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
              placeholder="Paste key clauses or the full contract text here..."
              className="min-h-[220px] w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] px-4 py-4 text-sm text-neutral-900 outline-none transition focus:border-[#b08d57]"
            />

            {errorMessage && (
              <div className="mt-4 rounded-2xl border border-red-200 bg-red-50 p-4 text-sm leading-6 text-red-700">
                {errorMessage}
              </div>
            )}

            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-[#8f7245]">
                Use legible source text and review clause evidence, policy status, and decision records before relying on the result.
              </div>

              <button
                onClick={runReview}
                disabled={loading || !hasInput}
                className="rounded-2xl bg-[#11110f] px-6 py-3 text-sm font-semibold text-stone-100 shadow-[0_10px_22px_rgba(80,60,30,0.14)] transition hover:bg-[#1a1a17] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Reviewing..." : "Run Executive Review"}
              </button>
            </div>
          </div>

          {result && (
            <>
              <div className="report-print-hidden space-y-8">
                <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr] xl:items-stretch">
                  <div className="flex h-full flex-col rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                          Decision Signal
                        </div>
                        <h2 className="mt-2 text-2xl font-semibold text-neutral-950">
                          {scoreBand(normalizedScore, result.severity)} exposure
                        </h2>
                        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
                          {primarySummary}
                        </p>
                      </div>

                      <div
                        className={`rounded-full border px-4 py-2 text-sm font-medium ${severityBadgeClass(
                          result.severity,
                        )}`}
                      >
                        {result.severity}
                      </div>
                    </div>

                    <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:mt-auto xl:grid-cols-4">
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                        <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                          Normalized exposure score
                        </div>
                        <div className="mt-2 text-2xl font-semibold text-neutral-950">
                          {normalizedScore}
                        </div>
                        <div className="mt-1 text-[11px] uppercase tracking-wide text-[#8f7245]">
                          Raw risk score: {rawRiskScore}
                        </div>
                      </div>
                      <div
                        className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4"
                        title={reliabilityAssessment.helper}
                      >
                        <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                          Reliability
                        </div>
                        <div className="mt-2 text-base font-semibold text-neutral-950">
                          {reliabilityAssessment.label}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                        <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                          Detected findings
                        </div>
                        <div className="mt-2 text-2xl font-semibold text-neutral-950">
                          {matchedRuleCount}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                        <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                          Generated
                        </div>
                        <div className="mt-2 text-base font-semibold text-neutral-950">
                          {reportGeneratedLabel}
                        </div>
                      </div>
                    </div>

                    <div className="mt-4 grid gap-3 md:grid-cols-2">
                      <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Primary Risk Type
                        </div>
                        <div className="mt-2 text-sm font-semibold text-neutral-950">
                          {decisionPrimaryRiskType}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Impact Area
                        </div>
                        <div className="mt-2 text-sm font-semibold text-neutral-950">
                          {decisionImpactArea}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Confidence Driver
                        </div>
                        <div className="mt-2 text-sm font-semibold text-neutral-950">
                          {decisionConfidenceDriver}
                        </div>
                      </div>
                      <div className="rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-4">
                        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8f7245]">
                          Signal Type
                        </div>
                        <div className="mt-2 text-sm font-semibold text-neutral-950">
                          Structural clause-level exposure
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex h-full flex-col rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                      Decision Posture
                    </div>
                    <div className="mt-3 text-2xl font-semibold text-neutral-950">
                      {posture?.label}
                    </div>
                    <p className="mt-3 text-sm leading-6 text-neutral-700">
                      {posture?.detail}
                    </p>

                    <div className="mt-5 rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                      <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                        Recommended next step
                      </div>
                      <p className="mt-2 text-sm leading-6 text-neutral-700">
                        {posture?.nextStep}
                      </p>
                    </div>

                    <div className="mt-3 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                            Scan decision
                          </div>
                          <div className="mt-1 text-sm font-semibold text-neutral-950">
                            {scanDecisionLabel(scanDecision.state)}
                          </div>
                        </div>
                        <select
                          value={(scanDecision.state as ScanDecisionValue) || "pending"}
                          onChange={(event) => void updateScanDecision(event.target.value as ScanDecisionValue)}
                          disabled={!activeScanId || decisionSavingKey === "scan"}
                          className="rounded-xl border border-[#dccaa8] bg-[#fffdf8] px-3 py-2 text-sm text-neutral-800 disabled:opacity-60"
                        >
                          {SCAN_DECISION_OPTIONS.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        {[
                          { label: "Accept scan", value: "accepted" as ScanDecisionValue },
                          { label: "Escalate scan", value: "escalated" as ScanDecisionValue },
                          { label: "Send for legal review", value: "sent_for_legal_review" as ScanDecisionValue },
                        ].map((action) => (
                          <button
                            key={action.value}
                            type="button"
                            onClick={() => void updateScanDecision(action.value)}
                            disabled={!activeScanId || decisionSavingKey === "scan"}
                            className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-3 py-1.5 text-xs font-semibold text-neutral-800 transition hover:bg-[#f3e4c6] disabled:cursor-not-allowed disabled:opacity-60"
                          >
                            {action.label}
                          </button>
                        ))}
                      </div>

                      <div className="mt-3 text-xs leading-5 text-[#8f7245]">
                        {scanDecision.updated_at
                          ? `Last action: ${formatReportTimestamp(scanDecision.updated_at)}`
                          : activeScanId
                            ? "No scan-level decision recorded yet."
                            : "Decision controls activate once the review is saved."}
                      </div>
                    </div>

                    {decisionMessage && (
                      <div className="mt-3 rounded-2xl border border-[#dccaa8] bg-[#fffcf6] p-3 text-xs leading-5 text-neutral-700">
                        {decisionMessage}
                      </div>
                    )}

                    <div className="mt-3 rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-3 xl:mt-auto">
                      <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                        Product boundary
                      </div>
                      <p className="mt-1.5 text-xs leading-5 text-neutral-600">
                        {reportBoundaryNotice}
                      </p>
                    </div>
                  </div>
                </div>

                <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                        Negotiation Priorities
                      </div>
                      <h3 className="mt-2 text-2xl font-semibold text-neutral-950">
                        Primary risk drivers
                      </h3>
                    </div>
                  </div>

                  {reportPriorityItems.length ? (
                    reportPriorityItems.length === 1 ? (
                      reportPriorityItems.map((item, index) => {
                        const category = item.category ?? "";
                        return (
                          <div
                            key={`negotiation-${item.title ?? "risk"}-${index}`}
                            className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-6"
                          >
                            <div className="grid gap-5 md:grid-cols-[1.15fr_0.85fr] md:items-start">
                              <div>
                                <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                                  Priority {index + 1}
                                </div>
                                <h4 className="mt-2 text-base font-semibold text-neutral-950">
                                  {item.title ?? "Unlabeled risk"}
                                </h4>
                                <p className="mt-3 text-sm leading-6 text-neutral-700">
                                  {negotiationPriority(category)}
                                </p>
                              </div>
                              <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                                <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                  Why first
                                </div>
                                <p className="mt-2 text-sm leading-6 text-neutral-700">
                                  {priorityReason(category)}
                                </p>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
                        {reportPriorityItems.map((item, index) => {
                          const category = item.category ?? "";
                          return (
                            <div
                              key={`negotiation-${item.title ?? "risk"}-${index}`}
                              className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-6"
                            >
                              <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                                Priority {index + 1}
                              </div>
                              <h4 className="mt-2 text-base font-semibold text-neutral-950">
                                {item.title ?? "Unlabeled risk"}
                              </h4>
                              <p className="mt-3 text-sm leading-6 text-neutral-700">
                                {negotiationPriority(category)}
                              </p>
                              <div className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                                <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                  Why first
                                </div>
                                <p className="mt-2 text-sm leading-6 text-neutral-700">
                                  {priorityReason(category)}
                                </p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )
                  ) : (
                    <div className="mt-6 rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5 text-sm text-[#8f7245]">
                      No material automated risk signals were elevated into negotiation priorities for this review. This remains a low-signal result, not a contract clearance outcome.
                    </div>
                  )}
                </div>

                <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                  <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                    Clause Evidence
                  </div>
                  <div className="mt-4 space-y-4">
                    {findings.length ? (
                      findings.map((finding, index) => {
                        const findingId = findingDecisionId(finding, index);
                        const decision = findingDecisions[findingId] ?? { finding_id: findingId, status: "unresolved" };
                        const policy = policyIndicator(finding);
                        const noteOpen = Boolean(decisionNotesOpen[findingId]);
                        const noteDraft = findingDecisionNotes[findingId] ?? decision.note ?? "";
                        const isTopRisk = index < 3;

                        return (
                        <div
                          key={`${findingId}-${index}`}
                          className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5"
                        >
                          <div className="flex flex-wrap items-start justify-between gap-3">
                            <div>
                              <h4 className="text-lg font-semibold text-neutral-950">
                                {finding.title ?? "Unlabeled finding"}
                              </h4>
                              <div className="mt-1 text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                                {finding.category ?? "uncategorized"}
                              </div>
                            </div>

                            <div className="rounded-full border border-[#dccaa8] bg-[#fffaf0] px-3 py-1 text-xs font-medium text-neutral-700">
                              {severityTone(finding.severity)} impact
                            </div>
                          </div>

                          {policy && (
                            <div className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                              <div className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold ${policy.className}`}>
                                {policy.label}
                              </div>
                              <p className="mt-2 text-sm leading-6 text-neutral-700">
                                {policy.detail}
                              </p>
                            </div>
                          )}

                          <div className="mt-4 grid gap-4 md:grid-cols-2">
                            <div>
                              <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                Why it matters
                              </div>
                              <p className="mt-2 text-sm leading-6 text-neutral-700">
                                {finding.rationale ?? consequenceSummary(finding.category)}
                              </p>
                            </div>
                            <div>
                              <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                Recommended focus
                              </div>
                              <p className="mt-2 text-sm leading-6 text-neutral-700">
                                {recommendedFocus(finding.category)}
                              </p>
                            </div>
                          </div>

                          {finding.matched_text && (
                            <div className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                              <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                Clause evidence
                              </div>
                              <p className="mt-2 text-sm leading-6 text-neutral-700">
                                {finding.matched_text}
                              </p>
                            </div>
                          )}

                          {isTopRisk && (
                            <details className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-4">
                              <summary className="cursor-pointer text-sm font-semibold text-neutral-950">
                                What would make this acceptable
                              </summary>
                              <div className="mt-3 flex flex-wrap gap-2">
                                {acceptableGuidance(finding).map((item) => (
                                  <span key={item} className="rounded-full border border-[#dccaa8] bg-[#fcf2df] px-3 py-1.5 text-xs font-medium text-[#6f552d]">
                                    {item}
                                  </span>
                                ))}
                              </div>
                            </details>
                          )}

                          <div className="mt-4 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4">
                            <div className="flex flex-wrap items-center justify-between gap-3">
                              <div>
                                <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                                  Decision status
                                </div>
                                <div className="mt-1 text-sm font-semibold text-neutral-950">
                                  {findingDecisionLabel(decision.status)}
                                </div>
                              </div>
                              <select
                                value={(decision.status as FindingDecisionValue) || "unresolved"}
                                onChange={(event) => void updateFindingDecision(findingId, event.target.value as FindingDecisionValue, noteDraft)}
                                disabled={!activeScanId || decisionSavingKey === findingId}
                                className="rounded-xl border border-[#dccaa8] bg-[#fffdf8] px-3 py-2 text-sm text-neutral-800 disabled:opacity-60"
                              >
                                {FINDING_DECISION_OPTIONS.map((option) => (
                                  <option key={option.value} value={option.value}>
                                    {option.label}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div className="mt-3 flex flex-wrap gap-2">
                              {[
                                { label: "Accept", value: "accepted" as FindingDecisionValue },
                                { label: "Redline", value: "redlined" as FindingDecisionValue },
                                { label: "Escalate", value: "escalated" as FindingDecisionValue },
                                { label: "Waive", value: "waived" as FindingDecisionValue },
                              ].map((action) => (
                                <button
                                  key={action.value}
                                  type="button"
                                  onClick={() => void updateFindingDecision(findingId, action.value, noteDraft)}
                                  disabled={!activeScanId || decisionSavingKey === findingId}
                                  className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-3 py-1.5 text-xs font-semibold text-neutral-800 transition hover:bg-[#f3e4c6] disabled:cursor-not-allowed disabled:opacity-60"
                                >
                                  {action.label}
                                </button>
                              ))}
                            </div>

                            <button
                              type="button"
                              onClick={() => setDecisionNotesOpen((current) => ({ ...current, [findingId]: !noteOpen }))}
                              className="mt-3 text-xs font-semibold text-[#765a2b] underline-offset-4 hover:underline"
                            >
                              {noteOpen ? "Hide decision note" : decision.note ? "Edit decision note" : "Add optional note"}
                            </button>

                            {noteOpen && (
                              <div className="mt-3">
                                <textarea
                                  value={noteDraft}
                                  onChange={(event) =>
                                    setFindingDecisionNotes((current) => ({ ...current, [findingId]: event.target.value }))
                                  }
                                  rows={3}
                                  placeholder="Add a short commercial rationale or exception note."
                                  className="w-full rounded-2xl border border-[#dccaa8] bg-[#fffdf8] p-3 text-sm leading-6 text-neutral-800 outline-none focus:border-[#b08d57]"
                                />
                                <div className="mt-2 flex justify-end">
                                  <button
                                    type="button"
                                    onClick={() =>
                                      void updateFindingDecision(
                                        findingId,
                                        (decision.status as FindingDecisionValue) || "unresolved",
                                        noteDraft,
                                      )
                                    }
                                    disabled={!activeScanId || decisionSavingKey === findingId}
                                    className="rounded-full bg-[#11110f] px-4 py-2 text-xs font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60"
                                  >
                                    Save note
                                  </button>
                                </div>
                              </div>
                            )}

                            <div className="mt-3 text-xs leading-5 text-[#8f7245]">
                              {decision.updated_at
                                ? `Last action: ${formatReportTimestamp(decision.updated_at)}`
                                : activeScanId
                                  ? "No finding-level outcome recorded yet."
                                  : "Decision controls activate once the review is saved."}
                            </div>
                          </div>
                        </div>
                        );
                      })
                    ) : (
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5 text-sm text-[#8f7245]">
                        No material automated risk signals were elevated into detailed findings for this review. This is a low-signal result, not a substitute for commercial or legal review.
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-3xl border border-[#d7c3a0] bg-[#fcf7ee] p-6 shadow-[0_10px_22px_rgba(80,60,30,0.05)]">
                    <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                          AI Review Notes
                        </div>
                        <h3 className="mt-2 text-2xl font-semibold text-neutral-950">
                          Secondary explanation layer
                        </h3>
                        <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-700">
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

                    {aiState === "available" && aiReview?.ai_summary && (
                      <div className="mt-6 space-y-5">
                        <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                              Overview
                            </div>
                            <p className="mt-3 text-sm leading-7 text-neutral-700">
                              {aiReview.ai_summary.overview}
                            </p>
                          </div>

                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                              Risk posture summary
                            </div>
                            <p className="mt-3 text-sm leading-7 text-neutral-700">
                              {aiReview.ai_summary.risk_posture_summary}
                            </p>
                          </div>
                        </div>

                        {(aiReview.ai_summary.negotiation_focus ?? []).length > 0 && (
                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                              Negotiation focus
                            </div>
                            <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                              {(aiReview.ai_summary.negotiation_focus ?? []).map((item) => (
                                <li
                                  key={item}
                                  className="rounded-xl border border-[#e3d4bb] bg-[#fcf7ee] px-4 py-3"
                                >
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {(aiReview.ai_summary.evidence_notes ?? []).length > 0 && (
                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                              Evidence notes
                            </div>
                            <div className="mt-4 space-y-4">
                              {(aiReview.ai_summary.evidence_notes ?? []).map((note, index) => (
                                <div
                                  key={`${note.rule_id ?? note.title ?? "evidence"}-${index}`}
                                  className="rounded-2xl border border-[#e3d4bb] bg-[#fcf7ee] p-4"
                                >
                                  <h4 className="text-sm font-semibold text-neutral-950">
                                    {note.title ?? "Evidence note"}
                                  </h4>
                                  <p className="mt-2 text-sm leading-6 text-neutral-700">
                                    {note.explanation}
                                  </p>
                                  {note.evidence_excerpt && (
                                    <div className="mt-3 rounded-xl border border-[#dccaa8] bg-[#fffaf0] p-3 text-sm leading-6 text-neutral-700">
                                      {note.evidence_excerpt}
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {(aiReview.ai_summary.uncertainty_notes ?? []).length > 0 && (
                          <div className="rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-5">
                            <div className="text-xs uppercase tracking-[0.2em] text-[#8f7245]">
                              Uncertainty notes
                            </div>
                            <ul className="mt-3 space-y-2 text-sm leading-6 text-neutral-700">
                              {(aiReview.ai_summary.uncertainty_notes ?? []).map((item) => (
                                <li
                                  key={item}
                                  className="rounded-xl border border-[#e3d4bb] bg-[#fcf7ee] px-4 py-3"
                                >
                                  {item}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
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
                          <option key={option} value={option}>
                            {option}
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
                        className="rounded-2xl bg-[#11110f] px-5 py-3 text-sm font-medium text-stone-100 transition hover:opacity-90"
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
