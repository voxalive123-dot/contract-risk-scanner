"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  ActionButton,
  blockedReasonFromStatus,
  DataTable,
  EmptyState,
  formatDate,
  InternalBlockedState,
  InternalShell,
  LoadingNotice,
  Panel,
  PLATFORM_OWNER_EMAIL,
  RawDataDisclosure,
  StatusBadge,
  type BlockedReason,
  type TableColumn,
} from "../internal-ui";

type UserProfile = {
  legal_identity?: { first_name?: string | null; last_name?: string | null; business_name?: string | null; role_title?: string | null };
  display_profile?: { display_name?: string | null; workspace_name?: string | null };
};

type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  account_status: string;
  created_at: string | null;
  organization_name: string | null;
  profile: UserProfile;
  subscription: { effective_plan: string | null; subscription_state: string | null; monthly_scan_limit: number | null };
  usage: { scan_count: number; monthly_scans_used: number };
};

type AccessGrant = { id: string; email: string | null; granted_plan: string; grant_type: string; scan_quota_override: number | null; status: string; effective_active: boolean; expires_at: string | null; organization_name: string | null };
type UsersPayload = { users?: User[] };
type GrantsPayload = { grants?: AccessGrant[] };

const filters = ["all", "active", "suspended", "disabled", "closure_requested", "tester", "owner"] as const;
type Filter = (typeof filters)[number];

async function loadJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin");
  return response.json() as Promise<T>;
}

function userName(user: User) {
  const legal = `${user.profile?.legal_identity?.first_name ?? ""} ${user.profile?.legal_identity?.last_name ?? ""}`.trim();
  return user.profile?.display_profile?.display_name || legal || "Profile not completed";
}

export default function InternalUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [grants, setGrants] = useState<AccessGrant[]>([]);
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<Filter>("all");
  const [message, setMessage] = useState("Loading users...");
  const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [testerEmail, setTesterEmail] = useState("");
  const [testerPlan, setTesterPlan] = useState("executive");
  const [testerDays, setTesterDays] = useState("14");
  const [testerLimit, setTesterLimit] = useState("");

  async function loadUsers(q = search) {
    const suffix = q ? `?search=${encodeURIComponent(q)}` : "";
    const [userData, grantData] = await Promise.all([
      loadJson<UsersPayload>(`/api/internal/ops/users${suffix}`),
      loadJson<GrantsPayload>("/api/internal/ops/access-grants").catch(() => ({ grants: [] })),
    ]);
    setUsers(userData.users ?? []);
    setGrants(grantData.grants ?? []);
    setMessage("");
    setBlockedReason(null);
  }

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      loadJson<UsersPayload>("/api/internal/ops/users"),
      loadJson<GrantsPayload>("/api/internal/ops/access-grants").catch(() => ({ grants: [] })),
    ])
      .then(([userData, grantData]) => {
        if (cancelled) return;
        setUsers(userData.users ?? []);
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

  const testerEmails = useMemo(() => new Set(grants.filter((grant) => grant.effective_active && grant.email).map((grant) => grant.email as string)), [grants]);

  const filteredUsers = users.filter((user) => {
    const haystack = `${user.email} ${user.organization_name ?? ""} ${userName(user)} ${user.profile?.legal_identity?.business_name ?? ""}`.toLowerCase();
    if (search && !haystack.includes(search.toLowerCase())) return false;
    if (filter === "all") return true;
    if (filter === "tester") return testerEmails.has(user.email);
    if (filter === "owner") return user.email === PLATFORM_OWNER_EMAIL || user.role === "owner";
    return user.account_status === filter;
  });

  async function runAction(user: User, action: string) {
    const ownerProtected = user.email === PLATFORM_OWNER_EMAIL && ["suspend", "disable", "soft-delete"].includes(action);
    if (ownerProtected) {
      setMessage("Platform owner lockout actions are blocked in the console. Use the recovery runbook for owner access repair.");
      return;
    }
    const destructive = ["suspend", "disable", "soft-delete"].includes(action);
    if (destructive && !window.confirm(`Confirm ${action.replace("-", " ")} for ${user.email}? This audited action changes account access.`)) return;
    const reason = window.prompt("Reason for this audited action");
    if (!reason) return;
    const response = await fetch(`/api/internal/ops/users/${user.id}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    const payload = await response.json().catch(() => null) as { setup_url?: string; setup_token?: string } | null;
    if (!response.ok) {
      setMessage("User action was rejected by backend permissions.");
      return;
    }
    setMessage(action === "reset-link" ? `Reset/setup link generated${payload?.setup_url ? `: ${payload.setup_url}` : payload?.setup_token ? `: ${payload.setup_token}` : "."}` : "User action recorded.");
    await loadUsers(search);
  }

  async function createTester(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await fetch("/api/internal/ops/testers/create", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: testerEmail,
        granted_plan: testerPlan,
        duration_days: Number(testerDays),
        scan_quota_override: testerLimit ? Number(testerLimit) : null,
        reason: "Owner-created tester access",
      }),
    });
    const data = await response.json().catch(() => null) as { setup_token?: string; status?: string } | null;
    if (!response.ok) {
      setMessage("Tester access could not be created.");
      return;
    }
    setTesterEmail("");
    setTesterLimit("");
    setMessage(data?.setup_token ? `Tester created. Setup token: ${data.setup_token}` : "Tester access created for existing account.");
    await loadUsers(search);
  }

  async function revokeGrant(grant: AccessGrant) {
    if (!window.confirm(`Revoke tester/free access for ${grant.email ?? grant.organization_name ?? grant.id}?`)) return;
    const reason = window.prompt("Reason for revoking tester/free access");
    if (!reason) return;
    const response = await fetch(`/api/internal/ops/access-grants/${grant.id}/revoke`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!response.ok) {
      setMessage("Grant revoke was rejected by backend permissions.");
      return;
    }
    setMessage("Tester/free access revoked.");
    await loadUsers(search);
  }

  const columns: TableColumn<User>[] = [
    { key: "user", label: "User", render: (user) => <div><div className="flex flex-wrap items-center gap-2 font-semibold text-neutral-950">{user.email}{user.email === PLATFORM_OWNER_EMAIL && <StatusBadge value="Platform Owner" tone="owner" />}{testerEmails.has(user.email) && <StatusBadge value="Tester" tone="warn" />}</div><div className="mt-1 text-neutral-600">{userName(user)}</div></div> },
    { key: "org", label: "Organisation", render: (user) => user.organization_name ?? "-" },
    { key: "role", label: "Role", render: (user) => <StatusBadge value={user.role} tone={user.email === PLATFORM_OWNER_EMAIL ? "owner" : "neutral"} /> },
    { key: "membership", label: "Membership", render: (user) => <StatusBadge value={user.is_active ? "active" : "inactive"} /> },
    { key: "account", label: "Account", render: (user) => <StatusBadge value={user.account_status} /> },
    { key: "created", label: "Created", render: (user) => formatDate(user.created_at) },
    { key: "activity", label: "Last activity", render: (user) => <div>{user.usage.monthly_scans_used} scans this month<div className="text-neutral-500">Last activity not exposed</div></div> },
    { key: "actions", label: "Actions", className: "min-w-[260px]", render: (user) => <div className="flex flex-wrap gap-2"><ActionButton onClick={() => setSelectedUser(user)}>View</ActionButton><ActionButton disabled={user.email === PLATFORM_OWNER_EMAIL} onClick={() => runAction(user, "suspend")}>Suspend</ActionButton><ActionButton onClick={() => runAction(user, "reactivate")}>Reactivate</ActionButton><ActionButton disabled={user.email === PLATFORM_OWNER_EMAIL} onClick={() => runAction(user, "disable")}>Disable</ActionButton><ActionButton onClick={() => runAction(user, "reset-link")}>Reset link</ActionButton><ActionButton disabled={user.email === PLATFORM_OWNER_EMAIL} tone="danger" onClick={() => runAction(user, "soft-delete")}>Soft delete</ActionButton></div> },
  ];

  return (
    <InternalShell eyebrow="User management" title="User control board" subtitle="Search, classify, repair, suspend, reactivate, and provision tester access through audited backend actions.">
      {message && <LoadingNotice label={message} />}
      {blockedReason && <InternalBlockedState reason={blockedReason} />}
      {!blockedReason && (
        <div className="mt-6 space-y-6">
          <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
            <Panel title="Users" subtitle="Owner account lockout controls are visually blocked to prevent accidental platform loss.">
              <div className="mt-5 flex flex-col gap-3 lg:flex-row">
                <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search email, name, or organisation" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
                <ActionButton tone="primary" onClick={() => loadUsers(search)}>Search</ActionButton>
              </div>
              <div className="mt-4 flex flex-wrap gap-2">
                {filters.map((item) => <ActionButton key={item} tone={filter === item ? "primary" : "neutral"} onClick={() => setFilter(item)}>{item.replace("_", " ")}</ActionButton>)}
              </div>
              <DataTable columns={columns} rows={filteredUsers} emptyLabel="No users match the selected search and filter." />
            </Panel>

            <div className="space-y-6">
              <Panel title="Create tester access" subtitle="Tester grants are non-revenue access and expire through backend entitlement checks.">
                <form onSubmit={createTester} className="mt-5 space-y-3">
                  <input type="email" required value={testerEmail} onChange={(event) => setTesterEmail(event.target.value)} placeholder="tester@example.com" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
                  <select value={testerPlan} onChange={(event) => setTesterPlan(event.target.value)} className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm"><option value="business">business access</option><option value="executive">executive access</option><option value="enterprise">enterprise access</option></select>
                  <input type="number" min="1" value={testerDays} onChange={(event) => setTesterDays(event.target.value)} className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm" placeholder="Expiry days" />
                  <input type="number" min="1" value={testerLimit} onChange={(event) => setTesterLimit(event.target.value)} className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm" placeholder="Optional scan limit" />
                  <button className="w-full rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100">Create tester access</button>
                </form>
              </Panel>
              <Panel title="Active tester/free grants">
                <div className="mt-4 space-y-3">
                  {grants.length === 0 && <EmptyState title="No active grants">Owner-granted tester or trial access will appear here.</EmptyState>}
                  {grants.map((grant) => <div key={grant.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-3 text-sm"><div className="font-semibold text-neutral-950">{grant.email ?? grant.organization_name ?? grant.id}</div><div className="mt-1 text-neutral-600">{grant.granted_plan} / expires {formatDate(grant.expires_at)}</div><div className="mt-3 flex gap-2"><StatusBadge value={grant.status} /><ActionButton tone="danger" onClick={() => revokeGrant(grant)}>Revoke</ActionButton><ActionButton disabled title="Backend action not connected yet">Extend</ActionButton></div></div>)}
                </div>
              </Panel>
            </div>
          </div>

          {selectedUser && <Panel title="User detail" action={<ActionButton onClick={() => setSelectedUser(null)}>Close</ActionButton>}><div className="mt-5 grid gap-4 md:grid-cols-3"><div><div className="text-xs uppercase tracking-[0.16em] text-[#8a6a34]">Identity</div><div className="mt-2 text-sm leading-6">{userName(selectedUser)}<br />{selectedUser.profile?.legal_identity?.business_name ?? "No business name stored"}</div></div><div><div className="text-xs uppercase tracking-[0.16em] text-[#8a6a34]">Entitlement</div><div className="mt-2 text-sm leading-6">{selectedUser.subscription.effective_plan ?? "-"}<br />{selectedUser.subscription.subscription_state ?? "-"}</div></div><div><div className="text-xs uppercase tracking-[0.16em] text-[#8a6a34]">Usage</div><div className="mt-2 text-sm leading-6">{selectedUser.usage.scan_count} total scans<br />{selectedUser.usage.monthly_scans_used} this month</div></div></div></Panel>}
          <RawDataDisclosure data={{ users, grants }} />
        </div>
      )}
    </InternalShell>
  );
}
