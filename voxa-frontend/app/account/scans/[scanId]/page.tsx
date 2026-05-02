"use client";

import { useEffect, useState } from "react";
import { AccountShell, Panel } from "../../account-ui";

type Props = { params: Promise<{ scanId: string }> };
type ScanDetail = { id: string; created_at: string | null; source_title: string | null; severity: string | null; risk_score: number; top_findings?: Array<{ title?: string; severity?: string; evidence?: string; rationale?: string }>; decision_state?: { state: string; reason_code?: string | null }; };

export default function AccountScanDetailPage({ params }: Props) {
  const [scan, setScan] = useState<ScanDetail | null>(null);
  const [message, setMessage] = useState("Loading report...");

  useEffect(() => {
    params.then(({ scanId }) => fetch(`/api/account/scans/${scanId}`, { cache: "no-store" }))
      .then(async (response) => { if (!response.ok) throw new Error("scan_unavailable"); return response.json(); })
      .then((data) => { setScan(data); setMessage(""); })
      .catch(() => setMessage("This scan could not be loaded for the signed-in account."));
  }, [params]);

  function printReport() {
    const date = new Date().toISOString().slice(0, 10);
    document.title = `VoxaRisk_Contract_Risk_Report_${date}`;
    window.print();
  }

  return <AccountShell eyebrow="Report detail" title="Contract risk report.">
    {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
    {scan && <div className="mt-6 space-y-6">
      <Panel title="Report summary"><div className="mt-5 grid gap-4 md:grid-cols-4"><div>Title<br /><span className="font-semibold text-neutral-950">{scan.source_title ?? "Untitled scan"}</span></div><div>Date<br /><span className="font-semibold text-neutral-950">{scan.created_at ?? "?"}</span></div><div>Severity<br /><span className="font-semibold text-neutral-950">{scan.severity ?? "unknown"}</span></div><div>Score<br /><span className="font-semibold text-neutral-950">{scan.risk_score}</span></div></div><button type="button" onClick={printReport} className="mt-5 rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100">Download PDF via browser print</button></Panel>
      <Panel title="Top findings"><div className="mt-5 space-y-4">{(scan.top_findings ?? []).length === 0 && <div className="text-sm text-neutral-600">No stored finding snapshot for this report.</div>}{(scan.top_findings ?? []).map((finding, index) => <div key={`${finding.title}-${index}`} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4"><div className="font-semibold text-neutral-950">{finding.title ?? "Finding"}</div><div className="mt-2 text-sm leading-6 text-neutral-700">{finding.rationale ?? finding.evidence ?? "Evidence stored in scan detail."}</div></div>)}</div></Panel>
    </div>}
  </AccountShell>;
}
