"use client";

import { FormEvent, useEffect, useState } from "react";
import { InternalShell, Panel } from "../internal-ui";

type UserProfile = {
  legal_identity?: { first_name?: string | null; last_name?: string | null };
};

type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  account_status: string;
  organization_name: string | null;
  profile: UserProfile;
  subscription: { effective_plan: string; subscription_state: string };
  usage: { scan_count: number; monthly_scans_used: number };
};

type UsersPayload = { users?: User[] };

export default function InternalUsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("Loading users...");
  const [testerEmail, setTesterEmail] = useState("");
  const [testerPlan, setTesterPlan] = useState("executive");
  const [testerDays, setTesterDays] = useState("14");

  async function loadUsers(q = "") {
    const suffix = q ? `?search=${encodeURIComponent(q)}` : "";
    const response = await fetch(`/api/internal/ops/users${suffix}`, { cache: "no-store" });
    if (!response.ok) throw new Error("users_unavailable");
    const data: UsersPayload = await response.json();
    setUsers(data.users ?? []);
    setMessage("");
  }

  useEffect(() => {
    let cancelled = false;
    fetch("/api/internal/ops/users", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("users_unavailable");
        return response.json() as Promise<UsersPayload>;
      })
      .then((data) => {
        if (cancelled) return;
        setUsers(data.users ?? []);
        setMessage("");
      })
      .catch(() => {
        if (cancelled) return;
        setMessage("Internal users are unavailable for this account.");
      });
    return () => { cancelled = true; };
  }, []);

  async function runAction(userId: string, action: string) {
    const reason = window.prompt("Reason for this audited action");
    if (!reason) return;
    const response = await fetch(`/api/internal/ops/users/${userId}/${action}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason }),
    });
    if (!response.ok) {
      setMessage("User action was rejected by backend permissions.");
      return;
    }
    setMessage("User action recorded.");
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
        reason: "Owner-created tester access",
      }),
    });
    const data: { setup_token?: string } | null = await response.json().catch(() => null);
    if (!response.ok) {
      setMessage("Tester access could not be created.");
      return;
    }
    setTesterEmail("");
    setMessage(data?.setup_token ? `Tester created. Setup token: ${data.setup_token}` : "Tester access created for existing account.");
    await loadUsers(search);
  }

  return (
    <InternalShell eyebrow="User management" title="Users, identity, and access state.">
      {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
      <div className="mt-6 grid gap-6 lg:grid-cols-[1fr_360px]">
        <Panel title="User search">
          <div className="mt-5 flex gap-3">
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search email" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
            <button type="button" onClick={() => loadUsers(search)} className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100">Search</button>
          </div>
          <div className="mt-5 overflow-x-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8]">
            <table className="min-w-full text-left text-xs text-neutral-700">
              <thead className="bg-[#f7ecd8] text-[11px] uppercase tracking-[0.16em] text-[#8a6a34]"><tr><th className="px-3 py-3">User</th><th className="px-3 py-3">Plan</th><th className="px-3 py-3">Usage</th><th className="px-3 py-3">Actions</th></tr></thead>
              <tbody>{users.map((user) => <tr key={user.id} className="border-t border-[#ead9bb]"><td className="px-3 py-3"><div className="font-semibold text-neutral-950">{user.email}</div><div>{user.organization_name ?? "No org"} / {user.account_status}</div><div>{user.profile?.legal_identity?.first_name ?? ""} {user.profile?.legal_identity?.last_name ?? ""}</div></td><td className="px-3 py-3">{user.subscription?.effective_plan} / {user.subscription?.subscription_state}</td><td className="px-3 py-3">{user.usage.scan_count} total / {user.usage.monthly_scans_used} month</td><td className="px-3 py-3"><div className="flex flex-wrap gap-2"><button type="button" onClick={() => runAction(user.id, "suspend")} className="rounded-lg border px-2 py-1">Suspend</button><button type="button" onClick={() => runAction(user.id, "reactivate")} className="rounded-lg border px-2 py-1">Reactivate</button><button type="button" onClick={() => runAction(user.id, "disable")} className="rounded-lg border px-2 py-1">Disable</button><button type="button" onClick={() => runAction(user.id, "reset-link")} className="rounded-lg border px-2 py-1">Reset link</button></div></td></tr>)}</tbody>
            </table>
          </div>
        </Panel>
        <Panel title="Tester access">
          <form onSubmit={createTester} className="mt-5 space-y-3">
            <input type="email" value={testerEmail} onChange={(event) => setTesterEmail(event.target.value)} placeholder="tester@example.com" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
            <select value={testerPlan} onChange={(event) => setTesterPlan(event.target.value)} className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm"><option value="executive">executive</option><option value="enterprise">enterprise</option></select>
            <input value={testerDays} onChange={(event) => setTesterDays(event.target.value)} className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm" />
            <button className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100">Create tester</button>
            <p className="text-xs leading-6 text-neutral-600">Tester grants are labelled owner grants, expire through backend entitlement checks, and do not enter revenue metrics.</p>
          </form>
        </Panel>
      </div>
    </InternalShell>
  );
}
