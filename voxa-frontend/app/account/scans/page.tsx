"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AccountShell, Panel } from "../account-ui";

type Scan = { id: string; created_at: string | null; source_title: string | null; severity: string | null; risk_score: number; confidence: number; source_type: string; };

export default function AccountScansPage() {
  const [scans, setScans] = useState<Scan[]>([]);
  const [query, setQuery] = useState("");
  const [severity, setSeverity] = useState("all");
  const [message, setMessage] = useState("Loading scans...");

  useEffect(() => {
    fetch("/api/account/scans", { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error("scan_history_unavailable"); return response.json(); })
      .then((data) => { setScans(data.scans ?? []); setMessage(""); })
      .catch(() => setMessage("Scan history is unavailable for this account."));
  }, []);

  const filtered = useMemo(() => scans.filter((scan) => {
    const text = `${scan.source_title ?? "Untitled"} ${scan.severity ?? ""}`.toLowerCase();
    const matchesQuery = !query || text.includes(query.toLowerCase());
    const matchesSeverity = severity === "all" || (scan.severity ?? "unknown") === severity;
    return matchesQuery && matchesSeverity;
  }), [scans, query, severity]);

  return <AccountShell eyebrow="Historical scans" title="Scan history and reports.">
    <Panel title="Search and filter">
      <div className="mt-5 grid gap-3 md:grid-cols-[1fr_220px]">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search by title or severity" className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
        <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]"><option value="all">All severities</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option><option value="unknown">Unknown</option></select>
      </div>
    </Panel>
    {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
    <div className="mt-6 overflow-x-auto rounded-xl border border-[#d8c49e] bg-[#fbf3e5]">
      <table className="min-w-full text-left text-sm text-neutral-700"><thead className="bg-[#f7ecd8] text-[11px] uppercase tracking-[0.16em] text-[#8a6a34]"><tr><th className="px-4 py-3">Date</th><th className="px-4 py-3">Title</th><th className="px-4 py-3">Severity</th><th className="px-4 py-3">Score</th><th className="px-4 py-3">Report</th></tr></thead><tbody>{filtered.map((scan) => <tr key={scan.id} className="border-t border-[#ead9bb]"><td className="px-4 py-3">{scan.created_at ?? "?"}</td><td className="px-4 py-3 font-semibold text-neutral-950">{scan.source_title ?? "Untitled scan"}</td><td className="px-4 py-3">{scan.severity ?? "unknown"}</td><td className="px-4 py-3">{scan.risk_score}</td><td className="px-4 py-3"><Link href={`/account/scans/${scan.id}`} className="font-semibold text-[#6f5328] underline decoration-[#c6aa72] underline-offset-4">Open</Link></td></tr>)}</tbody></table>
    </div>
  </AccountShell>;
}
