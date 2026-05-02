"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ActionButton,
  blockedReasonFromStatus,
  DataTable,
  formatDate,
  InternalBlockedState,
  InternalShell,
  LoadingNotice,
  MetricCard,
  Panel,
  RawDataDisclosure,
  StatusBadge,
  type BlockedReason,
  type TableColumn,
} from "../internal-ui";

type Scan = { id: string; request_id: string; risk_score: number; risk_density?: number | null; confidence?: number | null; ruleset_version?: string | null; created_at: string | null };
type Summary = { recent_scans: Scan[]; scan_usage: { this_month: number }; organizations: { quota_blocked_requests_this_month: number; error_operations_this_month: number } };
type Org = { id: string; name: string; account_count: number; scan_count: number; monthly_scans_used: number; effective_entitlement: { effective_plan: string; monthly_scan_limit: number } };
type OrgPayload = { organizations: Org[] };
const severities = ["all", "high", "medium", "low"] as const;
type SeverityFilter = (typeof severities)[number];
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
function severityFor(score: number) { if (score >= 70) return "high"; if (score >= 40) return "medium"; return "low"; }
export default function Page() {
  const [summary, setSummary] = useState<Summary | null>(null); const [orgs, setOrgs] = useState<Org[]>([]); const [message, setMessage] = useState("Loading scans..."); const [blockedReason, setBlockedReason] = useState<BlockedReason>(null); const [severity, setSeverity] = useState<SeverityFilter>("all"); const [query, setQuery] = useState("");
  useEffect(() => { let cancelled = false; Promise.all([loadJson<Summary>("/api/internal/ops/summary"), loadJson<OrgPayload>("/api/internal/ops/organizations")]).then(([summaryData, orgData]) => { if (cancelled) return; setSummary(summaryData); setOrgs(orgData.organizations ?? []); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const totalScans = orgs.reduce((sum, org) => sum + org.scan_count, 0);
  const recentScans = useMemo(() => (summary?.recent_scans ?? []).filter((scan) => { if (severity !== "all" && severityFor(scan.risk_score) !== severity) return false; if (query && !scan.request_id.toLowerCase().includes(query.toLowerCase())) return false; return true; }), [summary, severity, query]);
  const highRisk = (summary?.recent_scans ?? []).filter((scan) => severityFor(scan.risk_score) === "high").length;
  const columns: TableColumn<Scan>[] = [
    { key: "date", label: "Date", render: (scan) => formatDate(scan.created_at) },
    { key: "source", label: "Title/source", render: (scan) => <div><div className="font-semibold text-neutral-950">{scan.request_id}</div><div className="text-neutral-500">Source title not exposed by current endpoint</div></div> },
    { key: "org", label: "User/org", render: () => "Not exposed by current endpoint" },
    { key: "score", label: "Score", render: (scan) => scan.risk_score },
    { key: "severity", label: "Severity", render: (scan) => <StatusBadge value={severityFor(scan.risk_score)} tone={severityFor(scan.risk_score) === "high" ? "danger" : severityFor(scan.risk_score) === "medium" ? "warn" : "good"} /> },
    { key: "status", label: "Status", render: () => <StatusBadge value="stored" tone="good" /> },
    { key: "details", label: "Details", render: () => <ActionButton disabled title="Backend action not connected yet">View</ActionButton> },
  ];
  return <InternalShell eyebrow="Scans" title="Scan operations board" subtitle="Monitor stored scan activity, recent risk levels, quota blocks, and backend error signals without exposing customer reports publicly.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{summary && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-4"><MetricCard label="Total scans" value={totalScans} /><MetricCard label="Scans this month" value={summary.scan_usage.this_month} /><MetricCard label="High-risk recent" value={highRisk} tone={highRisk ? "danger" : "good"} detail="From recent scan feed" /><MetricCard label="Failed/error ops" value={summary.organizations.error_operations_this_month} tone={summary.organizations.error_operations_this_month ? "danger" : "good"} /></div><Panel title="Scan feed filters"><div className="mt-5 flex flex-col gap-3 lg:flex-row"><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search request/source ID" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />{severities.map((item) => <ActionButton key={item} tone={severity === item ? "primary" : "neutral"} onClick={() => setSeverity(item)}>{item}</ActionButton>)}</div><DataTable columns={columns} rows={recentScans} emptyLabel="No scans match the selected filters." /></Panel><Panel title="Organisation scan load"><DataTable columns={[{ key: "org", label: "Organisation", render: (org: Org) => <span className="font-semibold text-neutral-950">{org.name}</span> }, { key: "total", label: "Total scans", render: (org: Org) => org.scan_count }, { key: "month", label: "This month", render: (org: Org) => org.monthly_scans_used }, { key: "quota", label: "Quota", render: (org: Org) => `${org.monthly_scans_used} / ${org.effective_entitlement.monthly_scan_limit}` }, { key: "plan", label: "Plan", render: (org: Org) => <StatusBadge value={org.effective_entitlement.effective_plan} /> }]} rows={orgs} emptyLabel="No organisation scan usage available." /></Panel><RawDataDisclosure data={{ summary, orgs }} /></div>}</InternalShell>;
}
