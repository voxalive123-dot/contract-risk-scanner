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

type Entitlement = { source: string; subscription_state: string; effective_plan: string; monthly_scan_limit: number; paid_access: boolean; fail_closed: boolean };
type Org = { id: string; name: string; created_at: string | null; legacy_plan_type: string; legacy_plan_status: string; plan_limit: number; stripe_customer_id: string | null; stripe_subscription_id: string | null; effective_entitlement: Entitlement; subscription: { plan_name: string; status: string; source: string; external_subscription_id: string | null; external_customer_id: string | null } | null; billing_customer_reference: { provider: string; external_customer_id: string; billing_email: string | null } | null; account_count: number; member_count: number; pending_invite_count: number; scan_count: number; monthly_scans_used: number; status_badge: { label: string; tone: string }; platform_context: { status: string; canonical_org_name: string } | null };
type Payload = { overview: { total_organizations: number; active_organizations: number; restricted_organizations: number; total_accounts: number; total_memberships: number; scans_this_month: number; effective_plan_counts: Record<string, number> }; organizations: Org[] };
type Detail = { found: boolean; organization?: { name: string; billing_email: string | null; stripe_price_lookup_key: string | null }; accounts?: Array<{ email: string; role: string; is_active: boolean }>; memberships?: Array<{ email: string | null; role: string; status: string }>; recent_scans?: Array<{ request_id: string; risk_score: number; created_at: string | null }>; recent_usage?: Array<{ endpoint: string; status_code: number; created_at: string | null }>; effective_entitlement?: Entitlement };
const tabs = ["all", "paid", "owner-granted", "restricted", "legacy-internal"] as const;
type Tab = (typeof tabs)[number];
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
function tabLabel(tab: Tab) { return tab.replace("-", " / "); }
export default function Page() {
  const [data, setData] = useState<Payload | null>(null);
  const [message, setMessage] = useState("Loading organisations...");
  const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);
  const [tab, setTab] = useState<Tab>("all");
  const [search, setSearch] = useState("");
  const [detail, setDetail] = useState<Detail | null>(null);
  useEffect(() => { let cancelled = false; loadJson<Payload>("/api/internal/ops/organizations").then((payload) => { if (cancelled) return; setData(payload); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const orgs = useMemo(() => (data?.organizations ?? []).filter((org) => {
    const text = `${org.name} ${org.stripe_customer_id ?? ""} ${org.stripe_subscription_id ?? ""}`.toLowerCase();
    if (search && !text.includes(search.toLowerCase())) return false;
    if (tab === "paid") return org.effective_entitlement.paid_access && org.effective_entitlement.source === "subscription";
    if (tab === "owner-granted") return org.effective_entitlement.source === "owner_grant";
    if (tab === "restricted") return org.effective_entitlement.fail_closed || org.effective_entitlement.subscription_state === "restricted";
    if (tab === "legacy-internal") return org.platform_context !== null || org.effective_entitlement.source === "legacy_organization";
    return true;
  }), [data, search, tab]);
  async function openDetail(org: Org) { setDetail(await loadJson<Detail>(`/api/internal/ops/organizations?org_id=${encodeURIComponent(org.id)}`)); }
  const columns: TableColumn<Org>[] = [
    { key: "name", label: "Organisation", render: (org) => <div><div className="font-semibold text-neutral-950">{org.name}</div><div className="mt-1 text-neutral-500">Created {formatDate(org.created_at)}</div>{org.platform_context && <div className="mt-2"><StatusBadge value={org.platform_context.status} tone="owner" /></div>}</div> },
    { key: "plan", label: "Plan", render: (org) => <div><StatusBadge value={org.effective_entitlement.effective_plan} tone={org.effective_entitlement.paid_access ? "good" : "neutral"} /><div className="mt-2 text-neutral-600">{org.effective_entitlement.source}</div></div> },
    { key: "sub", label: "Subscription", render: (org) => <div><StatusBadge value={org.subscription?.status ?? org.effective_entitlement.subscription_state} /><div className="mt-2 text-neutral-600">{org.subscription?.source ?? "No stored subscription"}</div></div> },
    { key: "quota", label: "Quota", render: (org) => `${org.monthly_scans_used} / ${org.effective_entitlement.monthly_scan_limit}` },
    { key: "members", label: "Members", render: (org) => `${org.member_count} memberships / ${org.account_count} accounts` },
    { key: "stripe", label: "Stripe IDs", render: (org) => <div className="max-w-[260px] break-all"><div>{org.billing_customer_reference?.external_customer_id ?? org.stripe_customer_id ?? "No customer ID"}</div><div className="mt-1 text-neutral-500">{org.subscription?.external_subscription_id ?? org.stripe_subscription_id ?? "No subscription ID"}</div></div> },
    { key: "actions", label: "Actions", render: (org) => <ActionButton onClick={() => openDetail(org)}>Details</ActionButton> },
  ];
  return <InternalShell eyebrow="Organisations" title="Organisation control board" subtitle="Monitor customer organisations, entitlement source, billing linkage, quota, members, and platform/legacy context.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{data && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-4"><MetricCard label="Organisations" value={data.overview.total_organizations} detail={`${data.overview.active_organizations} active`} /><MetricCard label="Restricted" value={data.overview.restricted_organizations} tone={data.overview.restricted_organizations ? "warn" : "good"} /><MetricCard label="Accounts" value={data.overview.total_accounts} detail={`${data.overview.total_memberships} memberships`} /><MetricCard label="Scans month" value={data.overview.scans_this_month} /></div><Panel title="Organisation segments"><div className="mt-5 flex flex-col gap-3 lg:flex-row"><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search organisation or Stripe ID" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />{tabs.map((item) => <ActionButton key={item} tone={tab === item ? "primary" : "neutral"} onClick={() => setTab(item)}>{tabLabel(item)}</ActionButton>)}</div><DataTable columns={columns} rows={orgs} emptyLabel="No organisations match this segment." /></Panel>{detail && <Panel title="Organisation detail" action={<ActionButton onClick={() => setDetail(null)}>Close</ActionButton>}><div className="mt-5 grid gap-4 lg:grid-cols-4"><MetricCard label="Accounts" value={detail.accounts?.length ?? 0} /><MetricCard label="Memberships" value={detail.memberships?.length ?? 0} /><MetricCard label="Recent scans" value={detail.recent_scans?.length ?? 0} /><MetricCard label="Entitlement" value={detail.effective_entitlement?.effective_plan ?? "-"} detail={detail.effective_entitlement?.source} /></div><div className="mt-5 grid gap-4 lg:grid-cols-2"><div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-sm"><div className="font-semibold text-neutral-950">Members</div><div className="mt-3 space-y-2">{detail.memberships?.map((member) => <div key={`${member.email}-${member.role}`} className="flex justify-between gap-3"><span>{member.email ?? "Unknown"}</span><StatusBadge value={`${member.role} ${member.status}`} /></div>)}</div></div><div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-sm"><div className="font-semibold text-neutral-950">Recent usage</div><div className="mt-3 space-y-2">{detail.recent_usage?.map((usage) => <div key={`${usage.endpoint}-${usage.created_at}`} className="flex justify-between gap-3"><span>{usage.endpoint}</span><StatusBadge value={`${usage.status_code}`} tone={usage.status_code >= 500 ? "danger" : usage.status_code >= 400 ? "warn" : "good"} /></div>)}</div></div></div></Panel>}<RawDataDisclosure data={{ data, detail }} /></div>}</InternalShell>;
}
