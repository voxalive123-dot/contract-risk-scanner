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
};

type TopRisk = {
  rule_id?: string;
  title?: string;
  category?: string;
  severity?: number;
  weight?: number;
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
  };
  extraction_method?: string | null;
  confidence_hint?: number | null;
  source_type?: string | null;
  page_count?: number | null;
  has_extractable_text?: boolean | null;
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

type AIExplainResponse = {
  status?: "available" | "disabled" | "unavailable";
  model?: string;
  reason?: string;
  ai_summary?: AIReviewSummary;
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

function reviewReliability(confidence?: number | null) {
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

function lowSignalSummary() {
  return "No material automated risk signal was elevated in the reviewed text. This should be treated as a low-signal automated result, not as contract approval.";
}

function buildAIExplainPayload(result: AnalyzeResult) {
  return {
    risk_score: result.risk_score,
    severity: result.severity,
    flags: result.flags,
    findings: (result.findings ?? []).map((finding) => ({
      rule_id: finding.rule_id,
      title: finding.title,
      category: finding.category,
      severity: finding.severity,
      rationale: finding.rationale,
      matched_text: finding.matched_text,
    })),
    meta: {
      confidence: result.meta?.confidence ?? result.confidence_hint ?? null,
      top_risks: result.meta?.top_risks ?? [],
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
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);
  const previousTitleRef = useRef<string | null>(null);

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
              body: JSON.stringify({ text }),
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
    } catch (error) {
      setErrorMessage(
        `Analysis could not be completed at this time. Review the source text or file and try again. ${String(error)}`,
      );
    } finally {
        setLoading(false);
    }
  }

  async function generateAIReviewNotes() {
    if (!result || !accountContext?.entitlement.ai_review_notes_allowed) return;

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
        setAIMessage("AI Review Notes are available on eligible paid plans.");
        return;
      }

      if (!response.ok) {
        setAIReview(null);
        setAIState("unavailable");
        setAIMessage(
          "AI Review Notes could not be generated for this report. The deterministic VoxaRisk analysis remains available.",
        );
        return;
      }

      const aiPayload = payload as AIExplainResponse | null;

      if (aiPayload?.status === "available" && aiPayload.ai_summary) {
        setAIReview(aiPayload);
        setAIState("available");
        return;
      }

      setAIReview(null);
      setAIState(aiPayload?.status === "disabled" ? "disabled" : "unavailable");
      setAIMessage(
        "AI Review Notes could not be generated for this report. The deterministic VoxaRisk analysis remains available.",
      );
    } catch {
      setAIReview(null);
      setAIState("unavailable");
      setAIMessage(
        "AI Review Notes could not be generated for this report. The deterministic VoxaRisk analysis remains available.",
      );
    }
  }

  const normalizedScore = result?.meta?.normalized_score ?? result?.risk_score ?? 0;
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
  const reportGeneratedLabel = formatReportTimestamp(reportGeneratedAt);
  const reportPriorityItems = (topRisks.length ? topRisks : findings).slice(0, 3);
  const isLowSignalResult = (topRisks.length === 0 && findings.length === 0 && result?.severity === "LOW") || false;
  const executiveSummaryDetail = isLowSignalResult
    ? "Final acceptance should still consider commercial dependency, deal context, and professional review where appropriate."
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
    "VoxaRisk provides automated contract risk intelligence and decision-support observations. It does not provide legal advice, legal opinion, contract approval, or a guarantee of compliance. Users remain responsible for commercial and legal decisions and should obtain professional advice where appropriate.";

  function handlePrintReport() {
    if (!result) {
      setErrorMessage("Run a contract analysis first to generate a report.");
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
                Contract scanning, executive reporting, and export are available only inside a signed-in VoxaRisk account workspace.
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
                Contract Risk Workspace
              </div>
              <h1 className="mt-2.5 text-[2rem] font-semibold tracking-tight text-neutral-950">
                Executive review console
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-neutral-700">
                Paste contract text or upload a document to generate a structured risk review, negotiation focus, and executive report.
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
            <div className="mb-4 flex items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-semibold text-neutral-950">Contract Input</h2>
                <p className="mt-1 text-sm text-[#8f7245]">
                  Paste contract text or upload a supported file for executive review.
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
                  : "Text mode active. Paste the contract or the clauses that need review."}
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
                Use legible source text and review clause evidence before relying on the result.
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
                <div className="grid items-start gap-6 xl:grid-cols-[1.2fr_0.8fr]">
                  <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
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

                    <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-4">
                        <div className="text-xs uppercase tracking-wide text-[#8f7245]">
                          Exposure score
                        </div>
                        <div className="mt-2 text-2xl font-semibold text-neutral-950">
                          {normalizedScore}
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
                  </div>

                  <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
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

                    <div className="mt-3 rounded-2xl border border-[#ead9bc] bg-[#fffcf6] p-3">
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

                  <div className="mt-6 grid gap-4 lg:grid-cols-3">
                    {reportPriorityItems.length ? (
                      reportPriorityItems.map((item, index) => {
                        const category = item.category ?? "";
                        return (
                          <div
                            key={`negotiation-${item.title ?? "risk"}-${index}`}
                            className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5"
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
                      })
                    ) : (
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5 text-sm text-[#8f7245] lg:col-span-3">
                        No material automated risk signals were elevated into negotiation priorities for this scan. This remains a low-signal result, not a contract clearance outcome.
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)]">
                  <div className="text-xs font-medium uppercase tracking-[0.24em] text-[#8f7245]">
                    Clause Evidence
                  </div>
                  <div className="mt-4 space-y-4">
                    {findings.length ? (
                      findings.map((finding, index) => (
                        <div
                          key={`${finding.rule_id ?? "finding"}-${index}`}
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
                        </div>
                      ))
                    ) : (
                      <div className="rounded-2xl border border-[#dccaa8] bg-[#fcf2df] p-5 text-sm text-[#8f7245]">
                        No material automated risk signals were elevated into detailed findings for this scan. This is a low-signal result, not a substitute for commercial or legal review.
                      </div>
                    )}
                  </div>
                </div>

                {canUseAI && (
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
                        disabled={aiState === "loading"}
                        className="rounded-2xl border border-[#cdb78d] bg-[#fffaf0] px-5 py-3 text-sm font-semibold text-neutral-900 transition hover:bg-[#f3e4c6] disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        {aiState === "loading"
                          ? "Generating evidence-grounded AI notes..."
                          : "Generate AI Review Notes"}
                      </button>
                    </div>

                    {(aiState === "disabled" ||
                      aiState === "unavailable" ||
                      aiState === "denied" ||
                      aiState === "error") &&
                      aiMessage && (
                        <div className="mt-6 rounded-2xl border border-[#dccaa8] bg-[#fffaf0] p-4 text-sm leading-6 text-neutral-700">
                          {aiMessage}
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
                )}
              </div>

              <section className="rounded-3xl border border-[#dccaa8] bg-[#fffaf0] p-6 shadow-[0_12px_28px_rgba(80,60,30,0.06)] md:p-8">
                <div className="report-print-hidden border-b border-[#dccaa8] pb-6">
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
                      For a clean PDF, turn off browser Headers and footers in the print dialog.
                    </div>
                  </div>
                </div>

                <div
                  data-report-root
                  className="report-surface mx-auto mt-8 max-w-[920px] rounded-[24px] border border-[#dccaa8] bg-[#fffaf0] px-6 py-6 md:px-8 md:py-7"
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
                      <p>{executiveSummaryDetail}</p>
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
