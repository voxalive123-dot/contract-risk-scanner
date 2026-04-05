"use client";

import { useState } from "react";

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
  };
};

function severityTone(severity?: number) {
  if ((severity ?? 0) >= 4) return "High";
  if ((severity ?? 0) >= 3) return "Moderate";
  return "Low";
}

function recommendedFocus(category?: string) {
  switch (category) {
    case "jurisdiction":
      return "Review governing law and align dispute venue with your operating jurisdiction.";
    case "service":
      return "Tighten suspension triggers and require notice plus cure rights.";
    case "payment":
      return "Limit unilateral pricing changes or require approval and termination rights.";
    default:
      return "Review clause wording closely and negotiate narrower counterparty discretion.";
  }
}

function recommendedAction(category?: string) {
  switch (category) {
    case "jurisdiction":
      return "Negotiate";
    case "service":
      return "Negotiate";
    case "payment":
      return "Negotiate";
    default:
      return "Review";
  }
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
  const findings = result?.findings ?? [];
  const topRisks = result?.meta?.top_risks ?? [];

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8">
          <h1 className="text-4xl font-semibold tracking-tight text-gray-900">
            VoxaRisk Intelligence
          </h1>
          <p className="mt-2 text-sm text-gray-500">
            Contract Risk Analysis Dashboard
          </p>
        </div>

        <div className="mb-8 rounded-2xl border bg-white p-6 shadow-sm">
          <textarea
            className="w-full rounded-xl border border-gray-300 p-4 text-sm text-gray-800 outline-none transition focus:border-black"
            rows={6}
            placeholder="Paste contract text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />

          <button
            onClick={analyze}
            disabled={loading}
            className="mt-4 rounded-xl bg-black px-6 py-3 text-sm font-medium text-white transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? "Analyzing..." : "Analyze Contract"}
          </button>
        </div>

        {result && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <div className="rounded-2xl border bg-white p-6 shadow-sm">
              <div className="mb-2 text-sm text-gray-500">Risk Score</div>
              <div className="text-5xl font-bold text-gray-900">{normalizedScore}</div>
              <div className="mt-2 text-sm text-gray-600">
                Severity: <span className="font-medium">{result.severity}</span>
              </div>

              {contradictionCount > 0 && (
                <div className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-700">
                  {contradictionCount} contradiction{contradictionCount > 1 ? "s" : ""} detected
                </div>
              )}
            </div>

            <div className="rounded-2xl border bg-white p-6 shadow-sm lg:col-span-3">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Top Risks</h2>

              {topRisks.length > 0 ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  {topRisks.map((risk, i) => (
                    <div key={i} className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                      <div className="text-xs uppercase tracking-wide text-gray-500">
                        Rank {i + 1}
                      </div>
                      <div className="mt-2 text-lg font-semibold text-gray-900">
                        {risk.title ?? "Untitled risk"}
                      </div>
                      <div className="mt-2 text-sm text-gray-600">
                        Category: {risk.category ?? "n/a"}
                      </div>
                      <div className="mt-1 text-sm text-gray-600">
                        Severity: {severityTone(risk.severity)}
                      </div>
                      <div className="mt-1 text-sm text-gray-600">
                        Weight: {risk.weight ?? "n/a"}
                      </div>
                      <div className="mt-3 rounded-lg bg-white px-3 py-2 text-sm text-gray-700">
                        Recommended focus: {recommendedFocus(risk.category)}
                      </div>
                      <div className="mt-2 text-sm font-medium text-gray-900">
                        Recommended action: {recommendedAction(risk.category)}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500">No top risks returned.</div>
              )}
            </div>

            <div className="rounded-2xl border bg-white p-6 shadow-sm lg:col-span-2">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Executive Insight</h2>

              <div className="text-sm leading-7 text-gray-700">
                {result.severity === "HIGH" && (
                  <p>
                    This contract may expose significant financial or operational risk.
                    Several clauses materially strengthen the counterparty’s position and
                    deserve close review before acceptance.
                  </p>
                )}

                {result.severity === "MEDIUM" && (
                  <p>
                    This contract contains notable structural risk. The identified clauses
                    may affect leverage, flexibility, or downside exposure depending on
                    negotiation posture and commercial context.
                  </p>
                )}

                {result.severity === "LOW" && (
                  <p>
                    This contract shows relatively limited structural risk based on the
                    detected clause patterns. Even so, context-specific drafting and
                    commercial dependencies may still require review.
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-2xl border bg-white p-6 shadow-sm lg:col-span-3">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Flags</h2>

              {result.flags.length > 0 ? (
                <div className="flex flex-wrap gap-3">
                  {result.flags.map((flag, i) => (
                    <span
                      key={i}
                      className="rounded-full border border-gray-300 bg-gray-50 px-4 py-2 text-sm text-gray-800"
                    >
                      {flag}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500">No flags detected.</div>
              )}
            </div>

            <div className="rounded-2xl border bg-white p-6 shadow-sm lg:col-span-3">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Score Adjustments</h2>

              {adjustments.length > 0 ? (
                <div className="space-y-4">
                  {adjustments.map((adj, i) => (
                    <div key={i} className="rounded-xl bg-gray-50 p-4">
                      <div className="text-sm font-semibold uppercase tracking-wide text-gray-900">
                        {adj.type ?? "adjustment"} ({adj.effect ?? 0})
                      </div>
                      <div className="mt-1 text-sm text-gray-600">
                        {adj.reason ?? "No reason provided."}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500">No score adjustments were applied.</div>
              )}
            </div>

            <div className="rounded-2xl border bg-white p-6 shadow-sm lg:col-span-3">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">Key Findings</h2>

              {findings.length > 0 ? (
                <div className="space-y-4">
                  {findings.map((f, i) => (
                    <div key={i} className="rounded-xl border border-gray-200 bg-gray-50 p-5">
                      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                        <div>
                          <div className="text-lg font-semibold text-gray-900">
                            {f.title ?? "Untitled finding"}
                          </div>
                          <div className="mt-1 text-xs text-gray-500">
                            Severity: {severityTone(f.severity)} | Category: {f.category ?? "n/a"}
                          </div>
                        </div>
                      </div>

                      <div className="mt-4 text-sm leading-6 text-gray-700">
                        {f.rationale ?? "No rationale provided."}
                      </div>

                      <div className="mt-4 rounded-lg border border-gray-200 bg-white p-3 text-xs italic text-gray-500">
                        {f.matched_text ?? "No matched text available."}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-gray-500">No detailed findings returned.</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
