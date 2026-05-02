"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  blockedReasonFromStatus,
  DataTable,
  EmptyState,
  formatDate,
  formatMoneyMinor,
  InternalBlockedState,
  InternalShell,
  LoadingNotice,
  MetricCard,
  Panel,
  PLATFORM_OWNER_EMAIL,
  RawDataDisclosure,
  StatusBadge,
  type BlockedReason,
  type TableColumn,
} from "../internal-ui";

type InternalUser = {
  id: string;
  email: string;
  account_status: string;
  organization_name: string | null;
  subscription?: { effective_plan?: string | null; subscription_state?: string | null };
};

type RecentScan = { id: string; request_id: string; risk_score: number; created_at: string | null };
type RecentAction = { id: string; action_type: string; target_type: string; target_id?: string | null; reason?: string | null; created_at: string | null };
type AccessGrant = { id: string; email: string | null; grant_type: string; granted_plan: string; status: string; effective_active: boolean; expires_at: string | null };

type Summary = {
  staff_roles_enabled: Record<string, boolean>;
  users: { total: number; active: number; suspended: number; disabled: number; closure_requested: number };
  organizations: { total_organizations: number; active_organizations: number; restricted_organizations: number; scans_this_month: number; quota_blocked_requests_this_month: number; error_operations_this_month: number };
  subscription_breakdown: Record<string, number>;
  subscription_states: Record<string, number>;
  scan_usage: { this_month: number };
  recent_users: InternalUser[];
  recent_scans: RecentScan[];
  recent_actions: RecentAction[];
  revenue_summary: { amount_paid_minor_units: number; source: string; available: boolean; estimated: boolean };
};

type GrantPayload = { grants?: AccessGrant[] };

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin");
  return response.json() as Promise<T>;
}

export default function CommandCentrePage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [grants, setGrants] = useState<AccessGrant[]>([]);
  const [message, setMessage] = useState("Loading command centre...");
  const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([loadJson<Summary>("/api/internal/ops/summary"), loadJson<GrantPayload>("/api/internal/ops/access-grants").catch(() => ({ grants: [] }))])
      .then(([summaryData, grantData]) => {
        if (cancelled) return;
        setSummary(summaryData);
        setGrants(grantData.grants ?? []);
        setMessage("");
        setBlockedReason(null);
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setBlockedReason(error.message === "restricted" ? "restricted" : "signin");
        setMessage("");
      });
    return () => { cancelled = true; };
  }, []);

  const activeSubscriptions = summary ? (summary.subscription_states.active ?? 0) + (summary.subscription_states.trialing ?? 0) : 0;
  const activeGrants = grants.filter((grant) => grant.effective_active);
  const problemUsers = summary ? summary.users.suspended + summary.users.disabled + summary.users.closure_requested : 0;

  const scanColumns: TableColumn<RecentScan>[] = [
    { key: "date", label: "Date", render: (scan) => formatDate(scan.created_at) },
    { key: "request", label: "Scan", render: (scan) => <span className="font-semibold text-neutral-950">{scan.request_id}</span> },
    { key: "score", label: "Score", render: (scan) => <StatusBadge value={`${scan.risk_score}`} tone={scan.risk_score >= 70 ? "danger" : scan.risk_score >= 40 ? "warn" : "good"} /> },
  ];

  const actionColumns: TableColumn<RecentAction>[] = [
    { key: "time", label: "Time", render: (action) => formatDate(action.created_at) },
    { key: "action", label: "Action", render: (action) => <span className="font-semibold text-neutral-950">{action.action_type}</span> },
    { key: "target", label: "Target", render: (action) => `${action.target_type}${action.target_id ? ` / ${action.target_id}` : ""}` },
    { key: "reason", label: "Reason", render: (action) => action.reason ?? "-" },
  ];

  return (
    <InternalShell eyebrow="Executive overview" title="Owner Command Centre" subtitle="Operational control for users, organisations, access grants, scans, revenue truth, and audited internal authority.">
      {message && <LoadingNotice label={message} />}
      {blockedReason && <InternalBlockedState reason={blockedReason} />}
      {summary !== null && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-8">
            <MetricCard label="Total users" value={summary.users.total} detail={`${summary.users.active} active`} />
            <MetricCard label="Problem users" value={problemUsers} detail="Suspended, disabled, closure requested" tone={problemUsers ? "warn" : "good"} />
            <MetricCard label="Organisations" value={summary.organizations.total_organizations} detail={`${summary.organizations.active_organizations} active`} />
            <MetricCard label="Active subs" value={activeSubscriptions} detail="Stored subscription rows" tone={activeSubscriptions ? "good" : "neutral"} />
            <MetricCard label="Tester/trial" value={activeGrants.length} detail="Active owner-granted access" />
            <MetricCard label="Scans month" value={summary.scan_usage.this_month} detail={`${summary.organizations.quota_blocked_requests_this_month} quota blocks`} />
            <MetricCard label="Revenue truth" value={summary.revenue_summary.available ? formatMoneyMinor(summary.revenue_summary.amount_paid_minor_units) : "No invoices"} detail={summary.revenue_summary.source} />
            <MetricCard label="Owner identity" value={<StatusBadge value="Platform Owner" tone="owner" />} detail={PLATFORM_OWNER_EMAIL} />
          </div>

          <Panel title="Owner action board" subtitle="Shortcuts into the live operational control surfaces. Actions still require backend owner/internal permissions.">
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ["Manage users", "/internal/users"],
                ["Manage organisations", "/internal/orgs"],
                ["Review subscriptions", "/internal/subscriptions"],
                ["View revenue", "/internal/revenue"],
                ["View scans", "/internal/scans"],
                ["Audit log", "/internal/audit"],
                ["Staff permissions", "/internal/staff"],
                ["Create tester access", "/internal/users"],
              ].map(([label, href]) => (
                <Link key={href + label} href={href} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-4 text-sm font-semibold text-neutral-950 transition hover:border-[#11110f] hover:bg-[#f7ecd8]">
                  {label}
                </Link>
              ))}
            </div>
          </Panel>

          <div className="grid gap-6 xl:grid-cols-3">
            <Panel title="Recent users">
              <div className="mt-4 space-y-3">
                {summary.recent_users.length === 0 && <EmptyState title="No users yet">User records will appear here as accounts are created.</EmptyState>}
                {summary.recent_users.map((user) => (
                  <div key={user.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-3 text-sm">
                    <div className="flex flex-wrap items-center gap-2"><span className="font-semibold text-neutral-950">{user.email}</span>{user.email === PLATFORM_OWNER_EMAIL && <StatusBadge value="Platform Owner" tone="owner" />}</div>
                    <div className="mt-1 text-neutral-600">{user.organization_name ?? "No organisation"}</div>
                    <div className="mt-2"><StatusBadge value={user.account_status} /></div>
                  </div>
                ))}
              </div>
            </Panel>
            <Panel title="Recent scans">
              <DataTable columns={scanColumns} rows={summary.recent_scans} emptyLabel="No scans recorded yet." />
            </Panel>
            <Panel title="Recent audit actions">
              <DataTable columns={actionColumns} rows={summary.recent_actions} emptyLabel="No internal actions recorded yet." />
            </Panel>
          </div>

          <Panel title="System status" subtitle="Live operational signals from stored usage and entitlement data.">
            <div className="mt-5 grid gap-4 md:grid-cols-3">
              <MetricCard label="Restricted orgs" value={summary.organizations.restricted_organizations} tone={summary.organizations.restricted_organizations ? "warn" : "good"} />
              <MetricCard label="Server errors" value={summary.organizations.error_operations_this_month} detail="This month" tone={summary.organizations.error_operations_this_month ? "danger" : "good"} />
              <MetricCard label="Staff roles" value={Object.entries(summary.staff_roles_enabled).filter(([, enabled]) => enabled).length} detail="Configured role groups" />
            </div>
          </Panel>
          <RawDataDisclosure data={{ summary, grants }} />
        </div>
      )}
    </InternalShell>
  );
}
