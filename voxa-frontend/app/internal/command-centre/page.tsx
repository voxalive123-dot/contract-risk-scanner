"use client";

import { useEffect, useState } from "react";
import { InternalShell, Metric, Panel } from "../internal-ui";

type OrgOverview = { total_organizations: number; active_organizations: number };
type Summary = {
  users: { total: number; active: number; suspended: number };
  organizations: OrgOverview;
  subscription_breakdown: Record<string, number>;
  scan_usage: { this_month: number };
  recent_users: Array<{ id: string; email: string; account_status: string; organization_name: string | null }>;
  recent_scans: Array<{ id: string; request_id: string; risk_score: number; created_at: string | null }>;
  recent_actions: Array<{ id: string; action_type: string; target_type: string; created_at: string | null }>;
  revenue_summary: { amount_paid_minor_units: number; source: string; available: boolean; estimated: boolean };
};

export default function CommandCentrePage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [message, setMessage] = useState("Loading command centre...");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/internal/ops/summary", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("summary_unavailable");
        return response.json() as Promise<Summary>;
      })
      .then((data) => {
        if (cancelled) return;
        setSummary(data);
        setMessage("");
      })
      .catch(() => {
        if (cancelled) return;
        setMessage("Internal command centre is unavailable for this account.");
      });
    return () => { cancelled = true; };
  }, []);

  return (
    <InternalShell eyebrow="Executive overview" title="Business control, not guesswork.">
      {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
      {summary !== null && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 md:grid-cols-4 xl:grid-cols-6">
            <Metric label="Users" value={summary.users.total} detail={`${summary.users.active} active`} />
            <Metric label="Suspended" value={summary.users.suspended} />
            <Metric label="Organisations" value={summary.organizations.total_organizations} detail={`${summary.organizations.active_organizations} active`} />
            <Metric label="Scans month" value={summary.scan_usage.this_month} />
            <Metric label="Business" value={summary.subscription_breakdown.business ?? 0} />
            <Metric label="Revenue" value={summary.revenue_summary.available ? summary.revenue_summary.amount_paid_minor_units : "No data"} detail={summary.revenue_summary.source} />
          </div>
          <div className="grid gap-6 lg:grid-cols-3">
            <Panel title="Recent users"><div className="mt-4 space-y-3">{summary.recent_users.map((user) => <div key={user.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-3 text-sm"><div className="font-semibold text-neutral-950">{user.email}</div><div className="text-neutral-600">{user.organization_name ?? "No org"} / {user.account_status}</div></div>)}</div></Panel>
            <Panel title="Recent scans"><div className="mt-4 space-y-3">{summary.recent_scans.map((scan) => <div key={scan.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-3 text-sm"><div className="font-semibold text-neutral-950">{scan.request_id}</div><div className="text-neutral-600">Score {scan.risk_score} / {scan.created_at ?? "?"}</div></div>)}</div></Panel>
            <Panel title="Recent actions"><div className="mt-4 space-y-3">{summary.recent_actions.map((action) => <div key={action.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-3 text-sm"><div className="font-semibold text-neutral-950">{action.action_type}</div><div className="text-neutral-600">{action.target_type} / {action.created_at ?? "?"}</div></div>)}</div></Panel>
          </div>
        </div>
      )}
    </InternalShell>
  );
}
