"use client";

import { useMemo, useState } from "react";

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

function decisionPosture(
  severity: "LOW" | "MEDIUM" | "HIGH",
  topRiskCount: number,
  categories: string[],
) {
  const uniqueCategories = Array.from(new Set(categories.filter(Boolean)));
  const hasControlRisk = hasAnyCategory(uniqueCategories, CONTROL_CATEGORIES);
  const hasDisputeRisk = hasAnyCategory(uniqueCategories, DISPUTE_CATEGORIES);
  const hasEconomicRisk = hasAnyCategory(uniqueCategories, ECONOMIC_CATEGORIES);

  if (severity === "HIGH") {
    if (hasControlRisk && hasEconomicRisk) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. The counterparty appears to hold both operational leverage and disproportionate downside economics across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Escalate the control and economics clauses into a single redline package before any internal approval path starts.",
      };
    }
    if (hasControlRisk && hasDisputeRisk) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. The current drafting weakens both your practical operating position and your dispute leverage across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Push a redline round that rebalances venue, suspension, and termination mechanics before signature.",
      };
    }
    if (uniqueCategories.includes("indemnity")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Indemnity allocation appears capable of shifting disproportionate claim exposure onto your side across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Redraft the indemnity so scope, triggers, losses covered, and claim control rights are explicitly constrained.",
      };
    }
    if (uniqueCategories.includes("liability")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Liability allocation appears capable of producing disproportionate downside across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Force a redraft of the liability architecture, including caps, carve-outs, and asymmetry in exposure.",
      };
    }
    if (uniqueCategories.includes("payment")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. The counterparty appears able to move commercial terms after signature across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Redline the pricing and change-control mechanics so economics cannot drift without a real exit option.",
      };
    }
    if (uniqueCategories.includes("termination")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Exit optionality appears to sit disproportionately with the counterparty across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Rework termination rights, notice, and cure structure before the contract reaches approval.",
      };
    }
    if (uniqueCategories.includes("service")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Service continuity can be disrupted on terms that materially favor the counterparty across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Tighten suspension triggers, notice standards, and cure mechanics before accepting operational dependency.",
      };
    }
    if (uniqueCategories.includes("jurisdiction")) {
      return {
        label: "Hold / Renegotiate",
        detail: `Do not accept in current form. Venue and enforcement positioning appear structurally unfavorable across ${topRiskCount || 1} priority area${topRiskCount === 1 ? "" : "s"}.`,
        nextStep: "Push governing law and dispute forum back into a venue your business can realistically manage and enforce.",
      };
    }
    return {
      label: "Hold / Renegotiate",
      detail: `Do not accept in current form. Resolve the ${topRiskCount || 1} highest-value exposure point${topRiskCount === 1 ? "" : "s"} before signature.`,
      nextStep: "Escalate the flagged clauses into a focused redline round before any internal approval.",
    };
  }

  if (severity === "MEDIUM") {
    if (hasControlRisk && hasEconomicRisk) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if the combined control and economic exposure is commercially acceptable after negotiation or dependency analysis.",
        nextStep: "Test whether supplier leverage, fallback options, and deal economics justify accepting the current imbalance.",
      };
    }
    if (uniqueCategories.includes("indemnity")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if indemnity scope is commercially narrow and does not transfer broad third-party or direct-loss exposure onto your side.",
        nextStep: "Check indemnity scope, excluded losses, control of claims, and whether the allocation matches the real operating risk.",
      };
    }
    if (uniqueCategories.includes("liability")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if the liability structure is proportionate to the deal and does not create open-ended downside.",
        nextStep: "Check caps, carve-outs, and responsibility allocation against actual contract value and failure scenarios.",
      };
    }
    if (uniqueCategories.includes("payment")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if commercial movement after signature is either constrained or economically tolerable.",
        nextStep: "Verify whether the pricing mechanics preserve margin, budget certainty, and a realistic exit option.",
      };
    }
    if (uniqueCategories.includes("termination")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if the counterparty's stronger exit rights do not undermine planning certainty or revenue visibility.",
        nextStep: "Assess whether notice periods, cure rights, and replacement options are enough to absorb early exit risk.",
      };
    }
    if (uniqueCategories.includes("service")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if service interruption rights are sufficiently constrained for your operational dependency profile.",
        nextStep: "Test the suspension language against real service reliance, escalation paths, and restoration timelines.",
      };
    }
    if (uniqueCategories.includes("jurisdiction")) {
      return {
        label: "Conditional Review",
        detail: "Proceed only if the venue and enforcement position remain workable despite being less than ideal.",
        nextStep: "Check whether dispute cost, enforceability, and practical forum access are acceptable for this deal size.",
      };
    }
    return {
      label: "Conditional Review",
      detail: "Proceed only if the exposed clauses are commercially tolerable or can be narrowed with targeted negotiation.",
      nextStep: "Check whether the flagged clauses are acceptable within deal economics, fallback options, and supplier dependency.",
    };
  }

  return {
    label: "Proceed with Checks",
    detail: "No major structural alert is visible on current rule detection, but final acceptance should still depend on business dependency and deal context.",
    nextStep: "Complete final commercial checks and confirm no off-text dependency changes the practical risk.",
  };
}

export default function DashboardPage() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function analyze() {
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

  const summaryCategories = useMemo(
    () => [
      ...topRisks.map((risk) => risk.category ?? ""),
      ...findings.map((finding) => finding.category ?? ""),
    ],
    [topRisks, findings],
  );

  const primarySummary = useMemo(() => {
    if (!result) return "";
    return executiveSummary(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
    );
  }, [result, topRisks.length, findings.length, summaryCategories]);

  const posture = useMemo(() => {
    if (!result) return null;
    return decisionPosture(
      result.severity,
      topRisks.length || findings.length,
      summaryCategories,
    );
  }, [result, topRisks.length, findings.length, summaryCategories]);

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
              Automated contract risk intelligence to surface structural exposure, negotiation pressure points, and evidence-backed review priorities.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Engine</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">{rulesetVersion}</div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Confidence</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">{confidence.toFixed(2)}</div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Words</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">{wordCount}</div>
            </div>
            <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
              <div className="text-xs uppercase tracking-wide text-neutral-500">Rules Matched</div>
              <div className="mt-1 text-sm font-semibold text-neutral-900">{matchedRuleCount}</div>
            </div>
          </div>
        </div>

        <div className="mb-8 rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-neutral-950">Contract Input</h2>
              <p className="mt-1 text-sm text-neutral-500">Paste contract text to generate an executive risk view.</p>
            </div>
            <div className="text-xs text-neutral-400">Local secure proxy enabled</div>
          </div>

          <textarea
            className="w-full rounded-2xl border border-neutral-300 bg-white p-4 text-sm text-neutral-800 outline-none transition focus:border-black"
            rows={8}
            placeholder="Paste contract text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              onClick={analyze}
              disabled={loading}
              className="rounded-2xl bg-black px-6 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {loading ? "Analyzing..." : "Run Executive Review"}
            </button>
            <div className="text-sm text-neutral-500">
              Result emphasis: risk signal first, evidence second, technical detail last.
            </div>
          </div>
        </div>

        {result && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 gap-6 xl:grid-cols-4">
              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm xl:col-span-1">
                <div className="text-xs uppercase tracking-wide text-neutral-500">Risk Score</div>
                <div className="mt-3 text-6xl font-semibold tracking-tight text-neutral-950">
                  {normalizedScore}
                </div>
                <div className={`mt-3 inline-flex rounded-full border px-3 py-1 text-xs font-medium uppercase tracking-wide ${severityBadgeClass(result.severity)}`}>
                  {result.severity}
                </div>
                <div className="mt-4 text-sm text-neutral-600">
                  Exposure band: <span className="font-medium text-neutral-900">{scoreBand(normalizedScore, result.severity)}</span>
                </div>
                {contradictionCount > 0 && (
                  <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
                    {contradictionCount} contradiction{contradictionCount > 1 ? "s" : ""} detected across clause signals.
                  </div>
                )}
              </div>

              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm xl:col-span-3">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-xs uppercase tracking-wide text-neutral-500">Executive Reading</div>
                    <h2 className="mt-2 text-2xl font-semibold tracking-tight text-neutral-950">
                      Decision Signal
                    </h2>
                    <p className="mt-3 max-w-3xl text-sm leading-7 text-neutral-700">
                      {primarySummary}
                    </p>

                    {posture && (
                      <div className="mt-4 max-w-3xl rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                        <div className="text-xs uppercase tracking-wide text-neutral-500">Decision posture</div>
                        <div className="mt-2 text-base font-semibold text-neutral-950">{posture.label}</div>
                        <div className="mt-2 text-sm leading-6 text-neutral-700">{posture.detail}</div>
                        <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4">
                          <div className="text-xs uppercase tracking-wide text-neutral-500">Immediate next step</div>
                          <div className="mt-2 text-sm leading-6 text-neutral-700">{posture.nextStep}</div>
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="grid min-w-[260px] grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                      <div className="text-xs uppercase tracking-wide text-neutral-500">Top Risks</div>
                      <div className="mt-1 text-xl font-semibold text-neutral-950">{topRisks.length}</div>
                    </div>
                    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                      <div className="text-xs uppercase tracking-wide text-neutral-500">Flags</div>
                      <div className="mt-1 text-xl font-semibold text-neutral-950">{result.flags.length}</div>
                    </div>
                    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                      <div className="text-xs uppercase tracking-wide text-neutral-500">Adjustments</div>
                      <div className="mt-1 text-xl font-semibold text-neutral-950">{adjustments.length}</div>
                    </div>
                    <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3">
                      <div className="text-xs uppercase tracking-wide text-neutral-500">Suppressed</div>
                      <div className="mt-1 text-xl font-semibold text-neutral-950">{suppressedRuleCount}</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
              <div className="mb-5 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-neutral-950">Priority Risk Stack</h2>
                  <p className="mt-1 text-sm text-neutral-500">Highest-value review points first.</p>
                </div>
              </div>

              {topRisks.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
                  {topRisks.map((risk, i) => (
                    <div key={i} className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                      <div className="flex items-start justify-between gap-3">
                        <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">
                          Priority {i + 1}
                        </div>
                        <div className="rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                          {severityTone(risk.severity)}
                        </div>
                      </div>

                      <div className="mt-3 text-lg font-semibold text-neutral-950">
                        {risk.title ?? "Untitled risk"}
                      </div>

                      <div className="mt-3 flex flex-wrap gap-2">
                        <div className="rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                          {risk.category ?? "n/a"}
                        </div>
                        <div className="rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                          Impact weight {risk.weight ?? "n/a"}
                        </div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4 text-sm text-neutral-700">
                        <div className="text-xs uppercase tracking-wide text-neutral-500">Recommended focus</div>
                        <div className="mt-2 leading-6">{recommendedFocus(risk.category)}</div>
                      </div>

                      <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4 text-sm text-neutral-700">
                        <div className="text-xs uppercase tracking-wide text-neutral-500">Business consequence if ignored</div>
                        <div className="mt-2 leading-6">{consequenceSummary(risk.category)}</div>
                      </div>

                      <div className="mt-4 flex items-center justify-between">
                        <div className="text-xs uppercase tracking-wide text-neutral-500">Recommended action</div>
                        <div className="text-sm font-semibold text-neutral-950">
                          {recommendedAction(risk.category)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-neutral-500">No top risks returned.</div>
              )}
            </div>

            <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
              <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm xl:col-span-2">
                <h2 className="text-xl font-semibold text-neutral-950">Evidence and Findings</h2>
                <p className="mt-1 text-sm text-neutral-500">Underlying clause-level evidence behind the decision signal.</p>

                {findings.length > 0 ? (
                  <div className="mt-5 space-y-4">
                    {findings.map((f, i) => (
                      <div key={i} className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                        <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                          <div>
                            <div className="text-lg font-semibold text-neutral-950">
                              {f.title ?? "Untitled finding"}
                            </div>
                            <div className="mt-1 text-xs uppercase tracking-wide text-neutral-500">
                              {f.category ?? "n/a"} · {severityTone(f.severity)} severity
                            </div>
                          </div>

                          <div className="inline-flex rounded-full border border-neutral-300 bg-white px-3 py-1 text-xs font-medium text-neutral-700">
                            {f.rule_id ?? "rule unavailable"}
                          </div>
                        </div>

                        <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4">
                          <div className="text-xs uppercase tracking-wide text-neutral-500">Why this matters</div>
                          <div className="mt-2 text-sm leading-7 text-neutral-700">
                            {f.rationale ?? "No rationale provided."}
                          </div>
                        </div>

                        <div className="mt-4 rounded-2xl border border-neutral-200 bg-white p-4">
                          <div className="text-xs uppercase tracking-wide text-neutral-500">Clause evidence</div>
                          <div className="mt-2 text-sm italic leading-6 text-neutral-600">
                            {f.matched_text ?? "No matched text available."}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="mt-5 text-sm text-neutral-500">No detailed findings returned.</div>
                )}
              </div>

              <div className="space-y-6">
                <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-neutral-950">Flags</h2>
                  {result.flags.length > 0 ? (
                    <div className="mt-4 flex flex-wrap gap-2">
                      {result.flags.map((flag, i) => (
                        <span
                          key={i}
                          className="rounded-full border border-neutral-300 bg-neutral-50 px-3 py-2 text-sm text-neutral-800"
                        >
                          {flag}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 text-sm text-neutral-500">No flags detected.</div>
                  )}
                </div>

                <div className="rounded-3xl border border-neutral-200 bg-white p-6 shadow-sm">
                  <h2 className="text-lg font-semibold text-neutral-950">Score Adjustments</h2>
                  {adjustments.length > 0 ? (
                    <div className="mt-4 space-y-3">
                      {adjustments.map((adj, i) => (
                        <div key={i} className="rounded-2xl border border-neutral-200 bg-neutral-50 p-4">
                          <div className="text-sm font-semibold uppercase tracking-wide text-neutral-900">
                            {adj.type ?? "adjustment"} ({adj.effect ?? 0})
                          </div>
                          <div className="mt-1 text-sm leading-6 text-neutral-600">
                            {adj.reason ?? "No reason provided."}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="mt-4 text-sm text-neutral-500">No score adjustments were applied.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
