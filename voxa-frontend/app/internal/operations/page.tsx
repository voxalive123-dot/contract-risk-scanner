"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import SiteFooter from "../../site-footer";

type Entitlement = {
  effective_plan: string;
  subscription_state: string;
  paid_access: boolean;
  ai_review_notes_allowed: boolean;
  monthly_scan_limit: number;
  reason: string;
  source: string;
  fail_closed: boolean;
};

type PlatformContext = {
  status: "canonical_platform_org" | "legacy_platform_org";
  reason: string;
  canonical_org_id: string;
  canonical_org_name: string;
  owner_memberships: Array<{ membership_id: string; role: string; status: string }>;
} | null;

type OrgSummary = {
  id: string;
  name: string;
  legacy_plan_type: string;
  legacy_plan_status: string;
  plan_limit: number;
  stripe_customer_id?: string | null;
  stripe_subscription_id?: string | null;
  effective_entitlement: Entitlement;
  subscription: {
    plan_name: string;
    status: string;
    source: string;
    external_subscription_id?: string | null;
    external_customer_id?: string | null;
  } | null;
  billing_customer_reference: {
    provider: string;
    external_customer_id: string;
    billing_email: string | null;
  } | null;
  account_count: number;
  member_count: number;
  pending_invite_count: number;
  scan_count: number;
  monthly_scans_used: number;
  status_badge?: { label: string; tone: string };
  platform_context?: PlatformContext;
};

type OrgDetail = {
  found: boolean;
  organization?: {
    id: string;
    name: string;
    plan_type: string;
    plan_status: string;
    plan_limit: number;
    stripe_customer_id?: string | null;
    stripe_subscription_id?: string | null;
    stripe_price_id?: string | null;
    stripe_price_lookup_key?: string | null;
    billing_email?: string | null;
    current_period_end?: string | null;
    created_at?: string | null;
  };
  platform_context?: PlatformContext;
  current_subscription?: {
    plan_name: string;
    status: string;
    source: string;
    external_subscription_id?: string | null;
    external_customer_id?: string | null;
    current_period_end?: string | null;
  } | null;
  billing_customer_reference?: {
    provider: string;
    external_customer_id: string;
    billing_email: string | null;
  } | null;
  effective_entitlement?: Entitlement;
  diagnostics?: {
    effective_entitlement: { effective_plan: string; subscription_state: string; reason: string };
    mismatch_flags: Array<{ code: string; severity: string; message: string }>;
    billing_customer_reference: unknown;
    phase_10_subscription: unknown;
  };
  accounts?: Array<{ id: string; email: string; role: string; is_active: boolean; org_id: string; created_at: string | null }>;
  memberships?: Array<{ id: string; email: string | null; role: string; status: string }>;
  recent_invites?: Array<{ id: string; email: string; role: string; status: string }>;
  recent_scans?: Array<{ id: string; request_id: string; risk_score: number; created_at: string | null }>;
  recent_usage?: Array<{ id: string; endpoint: string; status_code: number; created_at: string | null }>;
  recent_signals?: Array<{ id: string; category: string; signal_type: string; severity: string; message: string }>;
  recent_webhooks?: Array<{ id: string; event_type: string; processing_status: string; error: string | null }>;
  recent_operator_actions?: OperatorAction[];
  manual_controls?: string[];
};

type OperatorAction = {
  id: string;
  actor_user_id: string;
  org_id: string | null;
  target_type: string;
  target_id: string | null;
  action_type: string;
  reason: string;
  created_at: string | null;
};

type WorkflowView = {
  read_only_truth: OrgDetail;
  operator_actions: OperatorAction[];
  manual_controls: string[];
  authority_notice: string;
};

type Overview = {
  total_organizations: number;
  total_accounts: number;
  total_memberships: number;
  active_organizations: number;
  restricted_organizations: number;
  legacy_plan_type_counts: Record<string, number>;
  effective_plan_counts: Record<string, number>;
  scans_this_month: number;
  quota_blocked_requests_this_month: number;
  recent_quota_blocked_requests: Array<{ id: string; endpoint: string; status_code: number; created_at: string | null }>;
  error_operations_this_month: number;
  recent_error_operations: Array<{ id: string; endpoint: string; status_code: number; created_at: string | null }>;
  ai_usage_this_month: number;
};

type SummaryPayload = {
  read_only: boolean;
  overview: Overview;
  recent_operator_actions: OperatorAction[];
  organizations: OrgSummary[];
};

function SiteHeader() {
  return (
    <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-5 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <Link href="/" className="flex items-center justify-center gap-4 md:justify-start">
          <div className="flex h-[76px] w-[76px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
            <img src="/brand/voxa-circle-logo.png" alt="VOXA" className="h-full w-full rounded-full object-cover object-center" />
          </div>
          <div className="leading-none">
            <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">VOXARISK</div>
            <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b5d2c]">INTERNAL OPERATIONS</div>
          </div>
        </Link>
        <nav className="flex items-center gap-3 text-sm text-neutral-700">
          <Link href="/internal/ops/access-grants" className="rounded-xl border border-[#d8c49e] px-4 py-2 font-semibold text-[#6f5328] transition hover:bg-[#fbf5ea]">Access grants</Link>
          <Link href="/account" className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]">Account</Link>
        </nav>
      </div>
    </header>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

function toneClass(tone?: string) {
  switch (tone) {
    case "danger":
      return "border-red-300 bg-red-50 text-red-900";
    case "success":
      return "border-emerald-300 bg-emerald-50 text-emerald-900";
    default:
      return "border-[#d8c49e] bg-[#fff8ea] text-[#6f5328]";
  }
}

export default function InternalOperationsPage() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [orgs, setOrgs] = useState<OrgSummary[]>([]);
  const [recentActions, setRecentActions] = useState<OperatorAction[]>([]);
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [detail, setDetail] = useState<OrgDetail | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowView | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [actionReason, setActionReason] = useState("");
  const [overridePlanType, setOverridePlanType] = useState("enterprise");
  const [overridePlanStatus, setOverridePlanStatus] = useState("manual_override");
  const [overridePlanLimit, setOverridePlanLimit] = useState("2000");
  const [cancelReasons, setCancelReasons] = useState<Record<string, string>>({});
  const [actionLoading, setActionLoading] = useState(false);

  async function loadSummary() {
    const response = await fetch("/api/internal/ops/organizations", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("summary_unavailable");
    }
    const data: SummaryPayload = await response.json();
    setOverview(data.overview ?? null);
    setRecentActions(data.recent_operator_actions ?? []);
    setOrgs(data.organizations ?? []);
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrapSummary() {
      try {
        const response = await fetch("/api/internal/ops/organizations", { cache: "no-store" });
        if (!response.ok) {
          throw new Error("summary_unavailable");
        }
        const data: SummaryPayload = await response.json();
        if (cancelled) return;
        setOverview(data.overview ?? null);
        setRecentActions(data.recent_operator_actions ?? []);
        setOrgs(data.organizations ?? []);
      } catch {
        if (cancelled) return;
        setMessage("Internal operations access is unavailable for this account.");
      }
    }

    void bootstrapSummary();
    return () => {
      cancelled = true;
    };
  }, []);

  async function loadWorkflow(orgId: string) {
    const response = await fetch(`/api/internal/ops/workflow?org_id=${encodeURIComponent(orgId)}`, { cache: "no-store" });
    if (!response.ok) {
      setMessage("Organisation workflow could not be loaded.");
      return null;
    }
    const data: WorkflowView = await response.json();
    setWorkflow(data);
    return data;
  }

  async function selectOrg(orgId: string) {
    setSelectedOrgId(orgId);
    setDetail(null);
    setWorkflow(null);
    setMessage(null);
    const response = await fetch(`/api/internal/ops/organizations?org_id=${encodeURIComponent(orgId)}`, { cache: "no-store" });
    if (!response.ok) {
      setMessage("Organisation detail could not be loaded.");
      return;
    }
    const data: OrgDetail = await response.json();
    setDetail(data);
    await loadWorkflow(orgId);
  }

  async function recordOperatorNote() {
    if (!selectedOrgId) return;
    setActionLoading(true);
    setMessage(null);
    const response = await fetch("/api/internal/ops/workflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "operator_note", org_id: selectedOrgId, reason: actionReason }),
    });
    setActionLoading(false);
    if (!response.ok) {
      setMessage("Operator note was rejected. A clear reason is required and internal access must be valid.");
      return;
    }
    setActionReason("");
    setMessage("Operator note recorded with audit history.");
    await loadSummary();
    await loadWorkflow(selectedOrgId);
  }

  async function cancelInvite(inviteId: string) {
    if (!selectedOrgId) return;
    setActionLoading(true);
    setMessage(null);
    const response = await fetch("/api/internal/ops/workflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type: "cancel_invite", invite_id: inviteId, reason: cancelReasons[inviteId] ?? "" }),
    });
    setActionLoading(false);
    if (!response.ok) {
      setMessage("Invite cancellation was rejected. Only pending unused invites can be cancelled with a clear reason.");
      return;
    }
    setCancelReasons((current) => ({ ...current, [inviteId]: "" }));
    setMessage("Pending invite cancelled with audit history.");
    await loadSummary();
    await selectOrg(selectedOrgId);
  }

  async function runOrganizationAction(
    type:
      | "restrict_organization"
      | "reactivate_organization"
      | "manual_override_organization"
      | "downgrade_organization_to_starter",
  ) {
    if (!selectedOrgId) return;
    setActionLoading(true);
    setMessage(null);
    const body =
      type === "manual_override_organization"
        ? {
            type,
            org_id: selectedOrgId,
            reason: actionReason,
            plan_type: overridePlanType,
            plan_status: overridePlanStatus,
            plan_limit: Number(overridePlanLimit),
          }
        : { type, org_id: selectedOrgId, reason: actionReason };
    const response = await fetch("/api/internal/ops/workflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    setActionLoading(false);
    if (!response.ok) {
      setMessage("Internal organisation action was rejected. Check the reason and any override fields.");
      return;
    }
    setActionReason("");
    setMessage("Internal organisation action recorded with audit history.");
    await loadSummary();
    await selectOrg(selectedOrgId);
  }

  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader />
        <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
          <div className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
            <Eyebrow>Internal governance</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              VoxaRisk operations console.
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              See system state, review entitlement truth, take bounded organisation actions, and keep every intervention auditable.
            </p>

            {message && <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">{message}</div>}

            {overview && (
              <div className="mt-8 grid gap-4 md:grid-cols-3 xl:grid-cols-6">
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Organisations</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.total_organizations}</div></div>
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Accounts</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.total_accounts}</div></div>
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Memberships</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.total_memberships}</div></div>
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Active / Restricted</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.active_organizations} / {overview.restricted_organizations}</div></div>
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Scans This Month</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.scans_this_month}</div></div>
                <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-xs uppercase tracking-[0.18em] text-[#8a6a34]">Quota Blocks / AI Usage</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{overview.quota_blocked_requests_this_month} / {overview.ai_usage_this_month}</div></div>
              </div>
            )}

            <div className="mt-8 grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
              <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                <div className="flex items-center justify-between gap-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Organisation management</div>
                  <div className="text-xs text-neutral-600">
                    Effective plans: {overview ? Object.entries(overview.effective_plan_counts).map(([key, value]) => `${key} ${value}`).join(" / ") : "—"}
                  </div>
                </div>
                <div className="mt-5 overflow-x-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8]">
                  <table className="min-w-full text-left text-xs text-neutral-700">
                    <thead className="bg-[#f7ecd8] text-[11px] uppercase tracking-[0.16em] text-[#8a6a34]">
                      <tr>
                        <th className="px-3 py-3">Organisation</th>
                        <th className="px-3 py-3">Legacy</th>
                        <th className="px-3 py-3">Effective</th>
                        <th className="px-3 py-3">Limit</th>
                        <th className="px-3 py-3">Scans</th>
                        <th className="px-3 py-3">Accounts</th>
                      </tr>
                    </thead>
                    <tbody>
                      {orgs.map((org) => (
                        <tr
                          key={org.id}
                          onClick={() => selectOrg(org.id)}
                          className={`cursor-pointer border-t border-[#ead9bb] ${selectedOrgId === org.id ? "bg-[#fff8ea]" : "hover:bg-[#fff8ea]"}`}
                        >
                          <td className="px-3 py-3">
                            <div className="font-semibold text-neutral-950">{org.name}</div>
                            <div className="text-[10px] text-neutral-500">{org.id}</div>
                            {org.platform_context && (
                              <div className="mt-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-[#8a6a34]">
                                {org.platform_context.status === "canonical_platform_org" ? "Canonical platform org" : "Legacy platform org"}
                              </div>
                            )}
                          </td>
                          <td className="px-3 py-3">{org.legacy_plan_type} / {org.legacy_plan_status}</td>
                          <td className="px-3 py-3">
                            <div>{org.effective_entitlement.effective_plan} / {org.effective_entitlement.subscription_state}</div>
                            <div className={`mt-1 inline-flex rounded-full border px-2 py-1 text-[10px] font-semibold ${toneClass(org.status_badge?.tone)}`}>{org.status_badge?.label ?? "Status"}</div>
                          </td>
                          <td className="px-3 py-3">{org.plan_limit} / effective {org.effective_entitlement.monthly_scan_limit}</td>
                          <td className="px-3 py-3">{org.monthly_scans_used} this month</td>
                          <td className="px-3 py-3">{org.account_count} / {org.member_count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Organisation detail</div>
                {!detail && <p className="mt-5 text-sm leading-7 text-neutral-700">Select an organisation to review account status, recent activity, and internal support history.</p>}
                {detail?.found && (
                  <div className="mt-5 space-y-5 text-sm leading-6 text-neutral-700">
                    <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                      <div className="font-semibold text-neutral-950">{detail.organization?.name}</div>
                      <div className="mt-2 text-xs text-neutral-500">{detail.organization?.id}</div>
                      {detail.platform_context && (
                        <div className="mt-2 rounded-lg border border-[#ead9bb] bg-[#fffaf0] p-3 text-xs leading-5 text-neutral-700">
                          <div className="font-semibold uppercase tracking-[0.14em] text-[#8a6a34]">
                            {detail.platform_context.status === "canonical_platform_org" ? "Canonical platform org" : "Legacy platform org"}
                          </div>
                          <div className="mt-2">Canonical name: {detail.platform_context.canonical_org_name}</div>
                          <div>Selection reason: {detail.platform_context.reason}</div>
                          {detail.platform_context.owner_memberships.length > 0 && (
                            <div>
                              Owner memberships: {detail.platform_context.owner_memberships.map((item) => `${item.role} / ${item.status}`).join(", ")}
                            </div>
                          )}
                        </div>
                      )}
                      <div className="mt-2">Legacy plan fields: {detail.organization?.plan_type} / {detail.organization?.plan_status} / limit {detail.organization?.plan_limit}</div>
                      <div>Effective plan: {detail.effective_entitlement?.effective_plan ?? detail.diagnostics?.effective_entitlement.effective_plan}</div>
                      <div>Subscription state: {detail.effective_entitlement?.subscription_state ?? detail.diagnostics?.effective_entitlement.subscription_state}</div>
                      <div>Resolver source: {detail.effective_entitlement?.source}</div>
                      <div>Reason: {detail.effective_entitlement?.reason ?? detail.diagnostics?.effective_entitlement.reason}</div>
                      {detail.current_subscription && <div>Current subscription: {detail.current_subscription.plan_name} / {detail.current_subscription.status} / {detail.current_subscription.source}</div>}
                      {detail.billing_customer_reference && <div>Billing customer: {detail.billing_customer_reference.external_customer_id}</div>}
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="font-semibold text-neutral-950">Accounts</div>
                        {(detail.accounts ?? []).length === 0 && <div className="mt-2">No linked accounts.</div>}
                        {(detail.accounts ?? []).map((item) => <div key={item.id} className="mt-2">{item.email} / {item.role} / {item.is_active ? "active" : "inactive"}</div>)}
                      </div>
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="font-semibold text-neutral-950">Memberships</div>
                        {(detail.memberships ?? []).map((item) => <div key={item.id} className="mt-2">{item.email} / {item.role} / {item.status}</div>)}
                      </div>
                    </div>

                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="font-semibold text-neutral-950">Recent invites</div>
                        {(detail.recent_invites ?? []).length === 0 && <div className="mt-2">No recent invites.</div>}
                        {(detail.recent_invites ?? []).map((item) => (
                          <div key={item.id} className="mt-4 rounded-lg border border-[#ead9bb] bg-[#fffaf0] p-3">
                            <div>{item.email} / {item.role} / {item.status}</div>
                            {item.status === "pending" && (
                              <div className="mt-3 space-y-2">
                                <input
                                  value={cancelReasons[item.id] ?? ""}
                                  onChange={(event) => setCancelReasons((current) => ({ ...current, [item.id]: event.target.value }))}
                                  placeholder="Reason for cancelling this pending invite"
                                  className="w-full rounded-lg border border-[#d2bd96] bg-white px-3 py-2 text-xs outline-none focus:border-[#8a6a34]"
                                />
                                <button
                                  type="button"
                                  disabled={actionLoading}
                                  onClick={() => cancelInvite(item.id)}
                                  className="rounded-lg border border-[#8a6a34] px-3 py-2 text-xs font-semibold text-[#6f5328] transition hover:bg-[#fff8ea] disabled:opacity-50"
                                >
                                  Cancel pending invite
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="font-semibold text-neutral-950">Recent scans and usage</div>
                        {(detail.recent_scans ?? []).map((scan) => <div key={scan.id} className="mt-2">{scan.request_id} / score {scan.risk_score} / {scan.created_at}</div>)}
                        {(detail.recent_usage ?? []).map((log) => <div key={log.id} className="mt-2">{log.endpoint} / {log.status_code} / {log.created_at}</div>)}
                      </div>
                    </div>

                    <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                      <div className="font-semibold text-neutral-950">Signals, webhooks, and mismatch flags</div>
                      {(detail.diagnostics?.mismatch_flags ?? []).length === 0 && <div className="mt-2">No mismatch flags.</div>}
                      {(detail.diagnostics?.mismatch_flags ?? []).map((flag) => <div key={flag.code} className="mt-2">{flag.severity}: {flag.code}</div>)}
                      {(detail.recent_signals ?? []).map((signal) => <div key={signal.id} className="mt-2">{signal.severity}: {signal.signal_type}</div>)}
                      {(detail.recent_webhooks ?? []).map((event) => <div key={event.id} className="mt-2">{event.event_type} / {event.processing_status}</div>)}
                    </div>

                    <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                      <div className="font-semibold text-neutral-950">Support workflow</div>
                      <p className="mt-2 text-xs leading-6 text-neutral-600">{workflow?.authority_notice ?? "Workflow actions are audited and do not override resolver-backed entitlement truth."}</p>
                      <textarea
                        value={actionReason}
                        onChange={(event) => setActionReason(event.target.value)}
                        placeholder="Record investigation note or reason for organisation action"
                        className="mt-4 min-h-24 w-full rounded-xl border border-[#d2bd96] bg-white px-4 py-3 text-sm outline-none focus:border-[#8a6a34]"
                      />
                      <div className="mt-3 flex flex-wrap gap-3">
                        <button type="button" disabled={actionLoading} onClick={recordOperatorNote} className="rounded-xl bg-[#11110f] px-4 py-2 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:opacity-50">Record operator note</button>
                        <button type="button" disabled={actionLoading} onClick={() => runOrganizationAction("restrict_organization")} className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-900 transition hover:bg-amber-100 disabled:opacity-50">Restrict organisation</button>
                        <button type="button" disabled={actionLoading} onClick={() => runOrganizationAction("reactivate_organization")} className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-2 text-sm font-semibold text-emerald-900 transition hover:bg-emerald-100 disabled:opacity-50">Reactivate organisation</button>
                        <button type="button" disabled={actionLoading} onClick={() => runOrganizationAction("downgrade_organization_to_starter")} className="rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-900 transition hover:bg-red-100 disabled:opacity-50">Downgrade to starter / restricted</button>
                      </div>
                      <div className="mt-5 rounded-xl border border-[#ead9bb] bg-[#fffaf0] p-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.14em] text-[#8a6a34]">Manual override</div>
                        <div className="mt-3 grid gap-3 md:grid-cols-3">
                          <select value={overridePlanType} onChange={(event) => setOverridePlanType(event.target.value)} className="rounded-lg border border-[#d2bd96] bg-white px-3 py-2 text-sm outline-none focus:border-[#8a6a34]">
                            <option value="starter">starter</option>
                            <option value="business">business</option>
                            <option value="executive">executive</option>
                            <option value="enterprise">enterprise</option>
                          </select>
                          <select value={overridePlanStatus} onChange={(event) => setOverridePlanStatus(event.target.value)} className="rounded-lg border border-[#d2bd96] bg-white px-3 py-2 text-sm outline-none focus:border-[#8a6a34]">
                            <option value="manual_override">manual_override</option>
                            <option value="active">active</option>
                            <option value="trialing">trialing</option>
                            <option value="restricted">restricted</option>
                          </select>
                          <input value={overridePlanLimit} onChange={(event) => setOverridePlanLimit(event.target.value)} className="rounded-lg border border-[#d2bd96] bg-white px-3 py-2 text-sm outline-none focus:border-[#8a6a34]" />
                        </div>
                        <button type="button" disabled={actionLoading} onClick={() => runOrganizationAction("manual_override_organization")} className="mt-3 rounded-xl bg-[#11110f] px-4 py-2 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:opacity-50">Apply manual override</button>
                      </div>
                      <div className="mt-5 border-t border-[#ead9bb] pt-4">
                        <div className="text-xs font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">Action history</div>
                        {(workflow?.operator_actions ?? []).length === 0 && <div className="mt-3 text-sm text-neutral-600">No operator actions recorded.</div>}
                        {(workflow?.operator_actions ?? []).map((action) => (
                          <div key={action.id} className="mt-3 rounded-lg border border-[#ead9bb] bg-[#fffaf0] p-3 text-xs leading-5 text-neutral-700">
                            <div className="font-semibold text-neutral-950">{action.action_type} / {action.target_type}</div>
                            <div>{action.reason}</div>
                            <div className="text-neutral-500">{action.created_at}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </section>
            </div>

            <div className="mt-8 grid gap-6 lg:grid-cols-2">
              <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Recent internal audit</div>
                {(recentActions ?? []).length === 0 && <div className="mt-4 text-sm text-neutral-600">No recent internal operator actions.</div>}
                {(recentActions ?? []).map((action) => (
                  <div key={action.id} className="mt-3 rounded-lg border border-[#ead9bb] bg-[#fffaf0] p-3 text-xs leading-5 text-neutral-700">
                    <div className="font-semibold text-neutral-950">{action.action_type} / {action.target_type}</div>
                    <div>{action.reason}</div>
                    <div className="text-neutral-500">{action.created_at}</div>
                  </div>
                ))}
              </section>

              <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Recent quota and error signals</div>
                <div className="mt-4 text-xs text-neutral-600">Recent quota-blocked requests</div>
                {(overview?.recent_quota_blocked_requests ?? []).length === 0 && <div className="mt-2 text-sm text-neutral-600">No recent quota blocks.</div>}
                {(overview?.recent_quota_blocked_requests ?? []).map((item) => <div key={item.id} className="mt-2 text-xs text-neutral-700">{item.endpoint} / {item.status_code} / {item.created_at}</div>)}
                <div className="mt-5 text-xs text-neutral-600">Recent error operations</div>
                {(overview?.recent_error_operations ?? []).length === 0 && <div className="mt-2 text-sm text-neutral-600">No recent error operations.</div>}
                {(overview?.recent_error_operations ?? []).map((item) => <div key={item.id} className="mt-2 text-xs text-neutral-700">{item.endpoint} / {item.status_code} / {item.created_at}</div>)}
              </section>
            </div>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
