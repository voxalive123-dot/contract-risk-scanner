"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

type AccountResponse = {
  user: { email: string };
  organization: { id: string; name: string };
  membership: { role: string; status: string };
  entitlement: {
    source: string;
    subscription_state: string;
    effective_plan: string;
    monthly_scan_limit: number;
    paid_access: boolean;
    ai_review_notes_allowed: boolean;
    reason: string;
  };
};

type TeamResponse = {
  memberships: Array<{ id: string; email: string | null; role: string; status: string }>;
  pending_invites: Array<{ id: string; email: string; role: string; status: string; expires_at: string | null }>;
};

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

export default function AccountPage() {
  const [account, setAccount] = useState<AccountResponse | null>(null);
  const [team, setTeam] = useState<TeamResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [teamLoading, setTeamLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [billingLoading, setBillingLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("member");
  const [inviteMessage, setInviteMessage] = useState<string | null>(null);
  const [inviteLoading, setInviteLoading] = useState(false);

  async function loadTeam() {
    setTeamLoading(true);
    try {
      const response = await fetch("/api/account/team", { cache: "no-store" });
      if (response.ok) {
        const data: TeamResponse = await response.json();
        setTeam(data);
      }
    } finally {
      setTeamLoading(false);
    }
  }

  useEffect(() => {
    async function loadAccount() {
      try {
        const response = await fetch("/api/account/me", { cache: "no-store" });
        if (!response.ok) {
          setMessage("Sign in is required to view account context.");
          return;
        }
        const data: AccountResponse = await response.json();
        setAccount(data);
        await loadTeam();
      } catch (error) {
        setMessage(`Account context could not be loaded. ${String(error)}`);
      } finally {
        setLoading(false);
      }
    }

    loadAccount();
  }, []);

  async function createInvite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInviteLoading(true);
    setInviteMessage(null);

    try {
      const response = await fetch("/api/account/team/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || typeof payload?.accept_url !== "string") {
        setInviteMessage("Team invite could not be created for this account role or email.");
        return;
      }

      setInviteEmail("");
      setInviteRole("member");
      setInviteMessage(`Invite created. Controlled acceptance link: ${payload.accept_url}`);
      await loadTeam();
    } catch (error) {
      setInviteMessage(`Team invite could not be created. ${String(error)}`);
    } finally {
      setInviteLoading(false);
    }
  }

  async function openBillingPortal() {
    setBillingLoading(true);
    setMessage(null);

    try {
      const response = await fetch("/api/account/billing/portal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ return_url: `${window.location.origin}/account` }),
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok || typeof payload?.url !== "string") {
        setMessage("Billing portal access is not available for this organisation yet.");
        return;
      }
      window.location.href = payload.url;
    } catch (error) {
      setMessage(`Billing portal could not be opened. ${String(error)}`);
    } finally {
      setBillingLoading(false);
    }
  }

  async function signOut() {
    await fetch("/api/account/logout", { method: "POST" });
    setAccount(null);
    setTeam(null);
    setMessage("Signed out.");
  }

  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader
          activeItem={account ? "account" : undefined}
          authMode={account ? "authenticated" : loading ? "auto" : "unauthenticated"}
          emphasizeSignIn={!loading && !account}
        />

        <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
          <div className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
            <Eyebrow>Account context</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              Organisation-linked account access.
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              This page shows the signed-in user, organisation membership, team context, and resolver-backed entitlement. Authentication identifies the account; subscription truth determines access.
            </p>

            {loading && <div className="mt-8 rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6 text-sm text-neutral-700">Loading account context...</div>}

            {!loading && message && !account && (
              <div className="mt-8 rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                <p className="text-sm leading-7 text-neutral-700">{message}</p>
                <Link href="/signin" className="mt-5 inline-flex rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">Sign in</Link>
              </div>
            )}

            {account && (
              <div className="mt-8 grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
                <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Identity and membership</div>
                  <div className="mt-5 space-y-4 text-sm leading-6 text-neutral-700">
                    <div><span className="font-semibold text-neutral-950">User:</span> {account.user.email}</div>
                    <div><span className="font-semibold text-neutral-950">Organisation:</span> {account.organization.name}</div>
                    <div><span className="font-semibold text-neutral-950">Organisation ID:</span> {account.organization.id}</div>
                    <div><span className="font-semibold text-neutral-950">Membership:</span> {account.membership.role} / {account.membership.status}</div>
                  </div>
                </section>

                <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Resolver-backed entitlement</div>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {[
                      ["Effective plan", account.entitlement.effective_plan],
                      ["Subscription state", account.entitlement.subscription_state],
                      ["Monthly scan limit", String(account.entitlement.monthly_scan_limit)],
                      ["AI Review Notes", account.entitlement.ai_review_notes_allowed ? "Available" : "Not available"],
                    ].map(([label, value]) => (
                      <div key={label} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8a6a34]">{label}</div>
                        <div className="mt-2 text-sm font-semibold text-neutral-950">{value}</div>
                      </div>
                    ))}
                  </div>
                  <p className="mt-5 rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-xs leading-6 text-neutral-600">
                    Account identity and role do not grant premium access. Paid features come from persisted subscription truth resolved through the VoxaRisk entitlement spine.
                  </p>
                </section>

                <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6 lg:col-span-2">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Team access</div>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-neutral-700">
                    Team membership links legitimate users to this organisation. Roles govern team actions only; paid entitlement remains organisation-level and resolver-backed.
                  </p>
                  {teamLoading && !team && <div className="mt-5 rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-sm text-neutral-700">Loading team context...</div>}
                  {team && (
                    <div className="mt-5 grid gap-4 lg:grid-cols-2">
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8a6a34]">Memberships</div>
                        <div className="mt-4 space-y-3 text-sm leading-6 text-neutral-700">
                          {team.memberships.map((membership) => (
                            <div key={membership.id} className="flex flex-col gap-1 rounded-lg border border-[#eadcc4] bg-[#fffaf0] p-3 sm:flex-row sm:items-center sm:justify-between">
                              <span>{membership.email ?? "Unknown user"}</span>
                              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#7b5d2c]">{membership.role} / {membership.status}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                      <div className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8a6a34]">Pending invites</div>
                        <div className="mt-4 space-y-3 text-sm leading-6 text-neutral-700">
                          {team.pending_invites.length === 0 && <div>No pending invites.</div>}
                          {team.pending_invites.map((invite) => (
                            <div key={invite.id} className="flex flex-col gap-1 rounded-lg border border-[#eadcc4] bg-[#fffaf0] p-3 sm:flex-row sm:items-center sm:justify-between">
                              <span>{invite.email}</span>
                              <span className="text-xs font-semibold uppercase tracking-[0.14em] text-[#7b5d2c]">{invite.role} / {invite.status}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}
                  {account.membership.role !== "member" && (
                    <form onSubmit={createInvite} className="mt-5 rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4">
                      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-[#8a6a34]">Create controlled invite</div>
                      <div className="mt-4 grid gap-3 md:grid-cols-[1fr_180px_auto]">
                        <input type="email" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} placeholder="user@example.com" className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]" required />
                        <select value={inviteRole} onChange={(event) => setInviteRole(event.target.value)} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]">
                          {account.membership.role === "owner" && <option value="admin">Admin</option>}
                          <option value="member">Member</option>
                        </select>
                        <button type="submit" disabled={inviteLoading} className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60">
                          {inviteLoading ? "Creating..." : "Create invite"}
                        </button>
                      </div>
                      {inviteMessage && <div className="mt-4 break-words rounded-xl border border-amber-200 bg-amber-50 p-4 text-xs leading-6 text-amber-800">{inviteMessage}</div>}
                    </form>
                  )}
                </section>

                <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6 lg:col-span-2">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Billing access</div>
                  <p className="mt-4 max-w-3xl text-sm leading-7 text-neutral-700">
                    Billing portal access uses the signed-in account, active membership, and the organisation&apos;s deterministic Stripe customer reference. It does not change entitlement authority.
                  </p>
                  {message && account && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">{message}</div>}
                  <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                    <button type="button" onClick={openBillingPortal} disabled={billingLoading} className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60">
                      {billingLoading ? "Opening billing portal..." : "Manage billing"}
                    </button>
                    <button type="button" onClick={signOut} className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-5 py-3 text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]">Sign out</button>
                  </div>
                </section>
              </div>
            )}
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
