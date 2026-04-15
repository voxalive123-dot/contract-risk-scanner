"use client";

import { ChangeEvent, useMemo, useRef, useState } from "react";

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
  if (severity === "HIGH") return "Elevated";
  if (severity === "MEDIUM") return score >= 35 ? "Elevated" : "Moderate";
  return score >= 20 ? "Moderate" : "Contained";
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

function recommendedAction(category?: string) {
  return categoryProfile(category).action;
}

function consequenceSummary(category?: string) {
  return categoryProfile(category).consequence;
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

  if (severity === "HIGH") {
    if (primaryCategory === "indemnity") {
      return `This contract presents material downside exposure driven by broad indemnity transfer. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (primaryCategory === "liability") {
      return `This contract presents material downside exposure driven primarily by liability structure. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (primaryCategory === "payment") {
      return `This contract presents material commercial exposure driven by one-sided economic movement after signature. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (primaryCategory === "termination") {
      return `This contract presents material control risk because exit optionality appears to sit disproportionately with the counterparty. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (primaryCategory === "service") {
      return `This contract presents material operational exposure because service continuity can be disrupted on terms that favor the counterparty. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (primaryCategory === "jurisdiction") {
      return `This contract presents material dispute exposure because enforcement and venue appear structurally unfavorable. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (hasControlRisk && hasDisputeRisk) {
      return `This contract presents material structural exposure because operational control rights and dispute positioning both appear to favor the counterparty. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    if (hasControlRisk && hasEconomicRisk) {
      return `This contract presents material structural exposure because the counterparty appears to hold both leverage over operations and disproportionate downside economics. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
    }
    return `This contract presents material structural exposure. ${riskCount} priority risk area${riskCount === 1 ? "" : "s"} should be addressed before acceptance.`;
  }

  if (severity === "MEDIUM") {
    if (primaryCategory === "indemnity") {
      return "This contract contains meaningful downside exposure because indemnity allocation may transfer disproportionate claim risk onto your side.";
    }
    if (primaryCategory === "liability") {
      return "This contract contains meaningful downside exposure through liability allocation that may exceed practical deal value.";
    }
    if (primaryCategory === "payment") {
      return "This contract contains meaningful commercial downside because the economics may shift after signature.";
    }
    if (primaryCategory === "termination") {
      return "This contract contains meaningful control risk because the counterparty appears to retain stronger exit flexibility.";
    }
    if (primaryCategory === "service") {
      return "This contract contains meaningful operational risk because service access may be interrupted on aggressive terms.";
    }
    if (primaryCategory === "jurisdiction") {
      return "This contract contains meaningful dispute risk because forum and enforcement mechanics may work against your operating position.";
    }
    if (hasControlRisk && hasEconomicRisk) {
      return "This contract contains meaningful downside exposure because commercial leverage and control rights appear to accumulate with the counterparty.";
    }
    return "This contract contains meaningful downside exposure. The current drafting should be reviewed with attention to leverage, control, and exit risk.";
  }

  return "This contract shows limited structural risk on current rule detection, but acceptance should still depend on commercial context and dependency exposure.";
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

  if (severity === "HIGH") {
    if (primaryCategory === "indemnity") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Indemnity allocation appears capable of shifting disproportionate claim exposure onto your side across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Redraft the indemnity so scope, triggers, losses covered, and claim control rights are explicitly constrained.",
      };
    }
    if (primaryCategory === "liability") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Liability allocation appears capable of producing disproportionate downside across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Force a redraft of the liability architecture, including caps, carve-outs, and asymmetry in exposure.",
      };
    }
    if (primaryCategory === "payment") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. The counterparty appears able to move commercial terms after signature across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Redline the pricing and change-control mechanics so economics cannot drift without a real exit option.",
      };
    }
    if (primaryCategory === "termination") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Exit optionality appears to sit disproportionately with the counterparty across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Rework termination rights, notice, and cure structure before the contract reaches approval.",
      };
    }
    if (primaryCategory === "service") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Service continuity appears exposed to counterparty-favored interruption mechanics across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Constrain suspension triggers, add notice discipline, and force a clear restoration mechanism.",
      };
    }
    if (primaryCategory === "jurisdiction") {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Venue and enforcement mechanics appear structurally unfavorable across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep:
          "Reposition governing law and dispute venue into a forum your business can realistically enforce and defend.",
      };
    }
    if (hasControlRisk && hasEconomicRisk) {
      return {
        label: "Hold / Renegotiate",
        detail:
          "Do not accept in current form. The contract appears to combine commercial downside with operational leverage that favors the counterparty.",
        nextStep:
          "Prioritize the top-ranked clauses first and remove the combination of economic drift and counterparty control.",
      };
    }
    if (hasControlRisk && hasDisputeRisk) {
      return {
        label: "Hold / Renegotiate",
        detail:
          "Do not accept in current form. The contract appears to combine operational leverage with structurally unfavorable dispute positioning.",
        nextStep:
          "Tighten control rights first, then move dispute mechanics into a venue aligned with your operating reality.",
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
        "The contract is not clean enough for passive acceptance. Meaningful structural issues are present, but they appear negotiable.",
      nextStep:
        "Use the priority risks to focus redlines on the clauses most likely to create leverage or downside.",
    };
  }

  return {
    label: "Proceed with Checks",
    detail:
      "No major structural alert is visible on current rule detection, but final acceptance should still depend on business dependency and deal context.",
    nextStep:
      "Complete final commercial checks and confirm no off-text dependency changes the practical risk.",
  };
}

export default function DashboardPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [inputMode, setInputMode] = useState<"text" | "file">("text");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadLabel, setUploadLabel] = useState("No file selected");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const cameraInputRef = useRef<HTMLInputElement | null>(null);

  async function analyzeText() {
    if (!text.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      });

      const textResponse = await res.text();

      if (!res.ok) {
        alert("Analysis error: " + textResponse);
        return;
      }

      const data: AnalyzeResult = JSON.parse(textResponse);
      setResult(data);
    } catch (err) {
      console.error("FETCH ERROR:", err);
      alert("Error analyzing contract: " + String(err));
    } finally {
      setLoading(false);
    }
  }

  async function analyzeFile(file: File) {
    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file, file.name);

      const res = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });

      const textResponse = await res.text();

      if (!res.ok) {
        alert("Analysis error: " + textResponse);
        return;
      }

      const data: AnalyzeResult = JSON.parse(textResponse);
      setResult(data);
    } catch (err) {
      console.error("UPLOAD ERROR:", err);
      alert("Error analyzing uploaded file: " + String(err));
    } finally {
      setLoading(false);
    }
  }

  async function runReview() {
    if (inputMode === "file") {
      if (!selectedFile) return;
      await analyzeFile(selectedFile);
      return;
    }

    await analyzeText();
  }

  function handleFileSelection(file: File | null) {
    setResult(null);
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

  const normalizedScore = result?.meta?.normalized_score ?? result?.risk_score ?? 0;
  const contradictionCount = result?.meta?.contradiction_count ?? 0;
  const adjustments = result?.meta?.score_adjustments ?? [];
  const findings = useMemo(() => result?.findings ?? [], [result?.findings]);
  const topRisks = useMemo(() => result?.meta?.top_risks ?? [], [result?.meta?.top_risks]);
  const confidence = result?.meta?.confidence ?? 0;
  const matchedRuleCount = result?.meta?.matched_rule_count ?? findings.length;
  const suppressedRuleCount = result?.meta?.suppressed_rule_count ?? 0;
  const rulesetVersion = result?.meta?.ruleset_version ?? "n/a";
  const wordCount = result?.meta?.word_count ?? 0;
  const hasTextInput = text.trim().length > 0;
  const hasFileInput = !!selectedFile;
  const hasInput = inputMode === "file" ? hasFileInput : hasTextInput;
  const isPreAnalysis = !result && !hasInput && !loading;

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

  const primarySummary = useMemo(() => {
    if (!result) return "";
    return executiveSummary(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);

  const posture = useMemo(() => {
    if (!result) return null;
    return decisionPosture(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
      primaryCategory,
    );
  }, [result, topRisks.length, findings.length, summaryCategories, primaryCategory]);

  const intakeGuidance =
    inputMode === "file"
      ? "Upload PDF, JPG, PNG, or WEBP. Camera capture will be processed as image OCR."
      : "Start with liability, indemnity, pricing, suspension, termination, and governing law clauses for the fastest first-pass signal.";

  return (
    <div className="min-h-screen bg-neutral-100 px-6 py-8 text-neutral-900 md:px-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-col gap-4 rounded-3xl border border-neutral-200 bg-white p-8 shadow-sm lg:flex-row lg:items-end lg:justify-between">
          <div>
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              VoxaRisk Intelligence
            </div>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-neutral-950">
              Executive Contract Risk Review
            </h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
              Automated contract risk intelligence to surface structural exposure,
              negotiation pressure points, and evidence-backed review priorities before
              commercial acceptance.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Engine</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">
                {result ? rulesetVersion : "Ready"}
              </div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Confidence</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">
                {result ? confidence.toFixed(2) : "Awaiting input"}
              </div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Words</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">
                {result ? wordCount : "No text"}
              </div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">
                Rules Matched
              </div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">
                {result ? matchedRuleCount : "No scan"}
              </div>
            </div>
          </div>
        </div>

        <div className="mb-8 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-neutral-950">Contract Input</h2>
              <p className="mt-1 text-sm text-neutral-500">
                Use pasted text or upload a contract file for structural exposure review.
              </p>
            </div>
            <div className="text-xs text-neutral-400">Local secure proxy enabled</div>
          </div>

          <div className="mb-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setInputMode("text")}
              className={`rounded-2xl border px-4 py-2 text-sm font-medium ${
                inputMode === "text"
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 bg-white text-neutral-700"
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
                  ? "border-neutral-900 bg-neutral-900 text-white"
                  : "border-neutral-200 bg-white text-neutral-700"
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
              className="rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700"
            >
              Use camera
            </button>
            {selectedFile && (
              <button
                type="button"
                onClick={clearUpload}
                className="rounded-2xl border border-neutral-200 bg-white px-4 py-2 text-sm font-medium text-neutral-700"
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

          <div className="mb-4 rounded-2xl border border-dashed border-neutral-300 bg-neutral-50 p-4">
            <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
              Intake mode
            </div>
            <div className="mt-2 text-sm text-neutral-700">
              {inputMode === "file"
                ? `File mode active. ${uploadLabel}`
                : "Text mode active. Paste contract language, key clauses, or the full agreement below."}
            </div>
          </div>

          <textarea
            value={text}
            onChange={(e) => {
              setText(e.target.value);
              if (e.target.value.trim()) {
                setInputMode("text");
                setSelectedFile(null);
                setUploadLabel("No file selected");
                if (fileInputRef.current) fileInputRef.current.value = "";
                if (cameraInputRef.current) cameraInputRef.current.value = "";
              }
            }}
            placeholder="Paste contract language, key clauses, or the full agreement text here..."
            className="min-h-[220px] w-full rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-sm text-neutral-900 outline-none transition focus:border-neutral-400"
          />

          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-neutral-500">{intakeGuidance}</div>

            <button
              onClick={runReview}
              disabled={loading || !hasInput}
              className="rounded-2xl bg-black px-6 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Reviewing..." : "Run Executive Review"}
            </button>
          </div>
        </div>

        {isPreAnalysis && (
          <div className="mb-8 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Best input
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Use the full agreement or the clauses that control liability,
                  indemnity, pricing movement, suspension, termination, and governing
                  law.
                </p>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  What returns
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  The engine will rank exposure, surface priority risks, and show
                  evidence-backed review points for negotiation or escalation.
                </p>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Review posture
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  This is a decision-support screen, not auto-approval. Use it to
                  identify where the contract may create asymmetric leverage or downside.
                </p>
              </div>
            </div>
          </div>
        )}

        {result && (
          <div className="space-y-8">
            <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div>
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                      Decision Signal
                    </div>
                    <h2 className="mt-2 text-2xl font-semibold text-neutral-950">
                      {scoreBand(normalizedScore, result.severity)} exposure
                    </h2>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-600">
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
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Risk score
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-neutral-950">
                      {normalizedScore}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Source type
                    </div>
                    <div className="mt-2 text-base font-semibold text-neutral-950">
                      {result.source_type ?? "text"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Extraction
                    </div>
                    <div className="mt-2 text-base font-semibold text-neutral-950">
                      {result.extraction_method ?? "direct"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Flags
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-neutral-950">
                      {result.flags.length}
                    </div>
                  </div>
                </div>

                <div className="mt-4 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Contradictions
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-neutral-950">
                      {contradictionCount}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Suppressed
                    </div>
                    <div className="mt-2 text-2xl font-semibold text-neutral-950">
                      {suppressedRuleCount}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      OCR confidence
                    </div>
                    <div className="mt-2 text-base font-semibold text-neutral-950">
                      {typeof result.confidence_hint === "number"
                        ? result.confidence_hint.toFixed(2)
                        : "n/a"}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Pages
                    </div>
                    <div className="mt-2 text-base font-semibold text-neutral-950">
                      {result.page_count ?? "n/a"}
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                  Decision Posture
                </div>
                <div className="mt-3 text-2xl font-semibold text-neutral-950">
                  {posture?.label}
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-600">
                  {posture?.detail}
                </p>

                <div className="mt-6 rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                  <div className="text-xs uppercase tracking-wide text-neutral-500">
                    Immediate next step
                  </div>
                  <p className="mt-2 text-sm leading-6 text-neutral-700">
                    {posture?.nextStep}
                  </p>
                </div>
              </div>
            </div>

            <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                      Priority Risks
                    </div>
                    <h3 className="mt-2 text-2xl font-semibold text-neutral-950">
                      Ranked review focus
                    </h3>
                  </div>
                </div>

                <div className="mt-6 space-y-4">
                  {(topRisks.length ? topRisks : findings).slice(0, 5).map((item, index) => {
                    const category = item.category ?? "";
                    const title = item.title ?? "Unlabeled risk";
                    const severity = item.severity ?? 0;

                    return (
                      <div
                        key={`${title}-${index}`}
                        className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5"
                      >
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div>
                            <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                              Priority {index + 1}
                            </div>
                            <h4 className="mt-2 text-lg font-semibold text-neutral-950">
                              {title}
                            </h4>
                          </div>

                          <div className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                            {severityTone(severity)} impact
                          </div>
                        </div>

                        <div className="mt-4 grid gap-4 md:grid-cols-3">
                          <div>
                            <div className="text-xs uppercase tracking-wide text-neutral-500">
                              Recommended focus
                            </div>
                            <p className="mt-2 text-sm leading-6 text-neutral-700">
                              {recommendedFocus(category)}
                            </p>
                          </div>

                          <div>
                            <div className="text-xs uppercase tracking-wide text-neutral-500">
                              Recommended action
                            </div>
                            <p className="mt-2 text-sm leading-6 text-neutral-700">
                              {recommendedAction(category)}
                            </p>
                          </div>

                          <div>
                            <div className="text-xs uppercase tracking-wide text-neutral-500">
                              Why this matters
                            </div>
                            <p className="mt-2 text-sm leading-6 text-neutral-700">
                              {consequenceSummary(category)}
                            </p>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                  Technical Detail
                </div>

                <div className="mt-4 space-y-3">
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Flags raised
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.flags.length ? (
                        result.flags.map((flag) => (
                          <span
                            key={flag}
                            className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs text-neutral-700"
                          >
                            {flag}
                          </span>
                        ))
                      ) : (
                        <span className="text-sm text-neutral-500">No flags returned.</span>
                      )}
                    </div>
                  </div>

                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                    <div className="text-xs uppercase tracking-wide text-neutral-500">
                      Score adjustments
                    </div>
                    <div className="mt-2 space-y-2">
                      {adjustments.length ? (
                        adjustments.map((adj, index) => (
                          <div key={index} className="text-sm text-neutral-700">
                            <span className="font-medium">{adj.type ?? "adjustment"}</span>
                            {typeof adj.effect === "number" ? ` (${adj.effect})` : ""} —{" "}
                            {adj.reason ?? "No reason provided"}
                          </div>
                        ))
                      ) : (
                        <div className="text-sm text-neutral-500">
                          No score adjustments returned.
                        </div>
                      )}
                    </div>
                  </div>

                  {result.source_type && result.source_type !== "text" && (
                    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                      <div className="text-xs uppercase tracking-wide text-neutral-500">
                        Intake diagnostics
                      </div>
                      <div className="mt-2 space-y-2 text-sm text-neutral-700">
                        <div>Source: {result.source_type}</div>
                        <div>Extraction: {result.extraction_method ?? "unknown"}</div>
                        <div>
                          Extractable text:{" "}
                          {typeof result.has_extractable_text === "boolean"
                            ? String(result.has_extractable_text)
                            : "n/a"}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
              <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                Clause Evidence
              </div>
              <div className="mt-4 space-y-4">
                {findings.length ? (
                  findings.map((finding, index) => (
                    <div
                      key={`${finding.rule_id ?? "finding"}-${index}`}
                      className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5"
                    >
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <h4 className="text-lg font-semibold text-neutral-950">
                            {finding.title ?? "Unlabeled finding"}
                          </h4>
                          <div className="mt-1 text-xs uppercase tracking-[0.2em] text-neutral-500">
                            {finding.category ?? "uncategorized"}
                          </div>
                        </div>

                        <div className="rounded-full border border-neutral-200 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                          {severityTone(finding.severity)} impact
                        </div>
                      </div>

                      {finding.rationale && (
                        <p className="mt-4 text-sm leading-6 text-neutral-700">
                          {finding.rationale}
                        </p>
                      )}

                      {finding.matched_text && (
                        <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4">
                          <div className="text-xs uppercase tracking-wide text-neutral-500">
                            Matched text
                          </div>
                          <p className="mt-2 text-sm leading-6 text-neutral-700">
                            {finding.matched_text}
                          </p>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5 text-sm text-neutral-500">
                    No detailed findings returned.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
