"use client";

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
  RawDataDisclosure,
  StatusBadge,
  type BlockedReason,
} from "../internal-ui";

type Summary = { subscription_breakdown: Record<string, number>; revenue_summary: { amount_paid_minor_units: number; source: string; available: boolean; estimated: boolean } };
type Org = { id: string; name: string; effective_entitlement: { source: string; effective_plan: string; paid_access: boolean }; subscription: { plan_name: string; status: string; external_customer_id: string | null; external_subscription_id: string | null } | null };
type OrgPayload = { organizations: Org[] };
type Grant = { id: string; email: string | null; organization_name: string | null; granted_plan: string; status: string; effective_active: boolean; expires_at: string | null };
type GrantPayload = { grants?: Grant[] };
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
export default function Page() {
  const [summary, setSummary] = useState<Summary | null>(null); const [orgs, setOrgs] = useState<Org[]>([]); const [grants, setGrants] = useState<Grant[]>([]); const [message, setMessage] = useState("Loading revenue..."); const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);
  useEffect(() => { let cancelled = false; Promise.all([loadJson<Summary>("/api/internal/ops/summary"), loadJson<OrgPayload>("/api/internal/ops/organizations"), loadJson<GrantPayload>("/api/internal/ops/access-grants").catch(() => ({ grants: [] }))]).then(([summaryData, orgData, grantData]) => { if (cancelled) return; setSummary(summaryData); setOrgs(orgData.organizations ?? []); setGrants(grantData.grants ?? []); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const paidCustomers = orgs.filter((org) => org.subscription && ["active", "trialing"].includes(org.subscription.status)).length;
  const nonRevenue = grants.filter((grant) => grant.effective_active);
  const paidRows = orgs.filter((org) => org.subscription);
  return <InternalShell eyebrow="Revenue" title="Revenue intelligence board" subtitle="Real stored invoice/payment records are separated from subscription state, estimates, and non-revenue access.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{summary && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-4"><MetricCard label="Real revenue" value={summary.revenue_summary.available ? formatMoneyMinor(summary.revenue_summary.amount_paid_minor_units) : "No invoice records"} detail={summary.revenue_summary.source} /><MetricCard label="Paid customers" value={paidCustomers} detail="Active/trialing stored subscriptions" /><MetricCard label="Non-revenue access" value={nonRevenue.length} detail="Tester/free/owner-granted" /><MetricCard label="Estimated plan value" value="Not calculated" detail="No fake revenue from plan labels" /></div>{!summary.revenue_summary.available && <EmptyState title="No live Stripe invoice/payment records are currently stored.">Revenue totals require stored Stripe invoice/payment records. Subscription labels are shown for operations only and are not counted as revenue here.</EmptyState>}<Panel title="Real subscription customers"><DataTable columns={[{ key: "org", label: "Organisation", render: (org: Org) => <span className="font-semibold text-neutral-950">{org.name}</span> }, { key: "plan", label: "Plan", render: (org: Org) => <StatusBadge value={org.subscription?.plan_name ?? org.effective_entitlement.effective_plan} /> }, { key: "status", label: "Status", render: (org: Org) => <StatusBadge value={org.subscription?.status ?? "missing"} /> }, { key: "customer", label: "Stripe customer", render: (org: Org) => <span className="break-all">{org.subscription?.external_customer_id ?? "-"}</span> }, { key: "sub", label: "Stripe subscription", render: (org: Org) => <span className="break-all">{org.subscription?.external_subscription_id ?? "-"}</span> }]} rows={paidRows} emptyLabel="No stored Stripe subscription rows." /></Panel><Panel title="Non-revenue access"><DataTable columns={[{ key: "who", label: "Email / Org", render: (grant: Grant) => grant.email ?? grant.organization_name ?? "-" }, { key: "plan", label: "Plan-equivalent", render: (grant: Grant) => <StatusBadge value={grant.granted_plan} tone="warn" /> }, { key: "expiry", label: "Expiry", render: (grant: Grant) => formatDate(grant.expires_at) }, { key: "status", label: "Status", render: (grant: Grant) => <StatusBadge value={grant.status} /> }]} rows={nonRevenue} emptyLabel="No active non-revenue grants." /></Panel><RawDataDisclosure data={{ summary, orgs, grants }} /></div>}</InternalShell>;
}
