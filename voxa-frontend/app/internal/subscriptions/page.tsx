"use client";

import { useEffect, useState } from "react";
import {
  blockedReasonFromStatus,
  DataTable,
  EmptyState,
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

type Summary = { subscription_breakdown: Record<string, number>; subscription_states: Record<string, number> };
type Entitlement = { source: string; subscription_state: string; effective_plan: string; monthly_scan_limit: number; paid_access: boolean };
type Org = { id: string; name: string; created_at: string | null; effective_entitlement: Entitlement; subscription: { plan_name: string; status: string; source: string; external_subscription_id: string | null; external_customer_id: string | null } | null; billing_customer_reference: { external_customer_id: string; provider: string } | null };
type OrgPayload = { organizations: Org[] };
type Grant = { id: string; email: string | null; granted_plan: string; status: string; effective_active: boolean };
type GrantPayload = { grants?: Grant[] };
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
export default function Page() {
  const [summary, setSummary] = useState<Summary | null>(null); const [orgs, setOrgs] = useState<Org[]>([]); const [grants, setGrants] = useState<Grant[]>([]); const [message, setMessage] = useState("Loading subscriptions..."); const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);
  useEffect(() => { let cancelled = false; Promise.all([loadJson<Summary>("/api/internal/ops/summary"), loadJson<OrgPayload>("/api/internal/ops/organizations"), loadJson<GrantPayload>("/api/internal/ops/access-grants").catch(() => ({ grants: [] }))]).then(([summaryData, orgData, grantData]) => { if (cancelled) return; setSummary(summaryData); setOrgs(orgData.organizations ?? []); setGrants(grantData.grants ?? []); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const subscriptionRows = orgs.filter((org) => org.subscription || org.billing_customer_reference || org.effective_entitlement.source === "owner_grant");
  const columns: TableColumn<Org>[] = [
    { key: "org", label: "Organisation", render: (org) => <div><div className="font-semibold text-neutral-950">{org.name}</div><div className="mt-1 text-neutral-500">{formatDate(org.created_at)}</div></div> },
    { key: "plan", label: "Plan", render: (org) => <StatusBadge value={org.subscription?.plan_name ?? org.effective_entitlement.effective_plan} tone={org.effective_entitlement.paid_access ? "good" : "neutral"} /> },
    { key: "status", label: "Status", render: (org) => <StatusBadge value={org.subscription?.status ?? org.effective_entitlement.subscription_state} /> },
    { key: "source", label: "Billing source", render: (org) => org.subscription?.source ?? org.effective_entitlement.source },
    { key: "customer", label: "Stripe customer", render: (org) => <span className="break-all">{org.subscription?.external_customer_id ?? org.billing_customer_reference?.external_customer_id ?? "-"}</span> },
    { key: "sub", label: "Stripe subscription", render: (org) => <span className="break-all">{org.subscription?.external_subscription_id ?? "-"}</span> },
    { key: "limit", label: "Scan limit", render: (org) => org.effective_entitlement.monthly_scan_limit },
  ];
  return <InternalShell eyebrow="Subscriptions" title="Subscription state board" subtitle="Stored Stripe subscription truth, entitlement source, and non-revenue owner-granted access are separated clearly.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{summary && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-4"><MetricCard label="Business" value={summary.subscription_breakdown.business ?? 0} /><MetricCard label="Executive" value={summary.subscription_breakdown.executive ?? 0} /><MetricCard label="Enterprise" value={summary.subscription_breakdown.enterprise ?? 0} /><MetricCard label="Owner-granted" value={grants.filter((grant) => grant.effective_active).length} detail="Tester/trial, not revenue" /></div><Panel title="Subscription states"><div className="mt-5 grid gap-3 md:grid-cols-4">{Object.entries(summary.subscription_states).length === 0 ? <EmptyState title="No stored subscriptions">No live Stripe subscription records are currently stored.</EmptyState> : Object.entries(summary.subscription_states).map(([state, count]) => <MetricCard key={state} label={state} value={count} tone={state === "active" || state === "trialing" ? "good" : state === "past_due" || state === "unpaid" ? "warn" : "neutral"} />)}</div></Panel><Panel title="Subscription table" subtitle="Rows use stored subscription/customer records only; no Stripe identifiers are fabricated.">{subscriptionRows.length === 0 && <EmptyState title="No real subscription data">No stored Stripe customer or subscription rows are available yet. Owner-granted tester access is tracked separately and does not count as revenue.</EmptyState>}<DataTable columns={columns} rows={subscriptionRows} emptyLabel="No subscription rows to show." /></Panel><Panel title="Free, tester, and owner-granted access"><DataTable columns={[{ key: "email", label: "Email", render: (grant: Grant) => grant.email ?? "-" }, { key: "plan", label: "Plan-equivalent", render: (grant: Grant) => <StatusBadge value={grant.granted_plan} tone="warn" /> }, { key: "status", label: "Status", render: (grant: Grant) => <StatusBadge value={grant.status} /> }]} rows={grants} emptyLabel="No active owner-granted access records." /></Panel><RawDataDisclosure data={{ summary, orgs, grants }} /></div>}</InternalShell>;
}
