"use client";

import Link from "next/link";
import { useState } from "react";

type UserControlPayload = {
  found: boolean;
  email: string;
  user: null | {
    id: string;
    email: string;
    role: string;
    is_active: boolean;
    org_id: string;
    created_at: string | null;
  };
  memberships: Array<{
    id: string;
    org_id: string;
    organization_name: string | null;
    role: string;
    status: string;
    created_at: string | null;
  }>;
  invites: Array<{
    id: string;
    email: string;
    role: string;
    status: string;
    expires_at: string | null;
    accepted_at: string | null;
    created_at: string | null;
  }>;
  password_tokens: Array<{
    id: string;
    purpose: string;
    status: string;
    expires_at: string | null;
    used_at: string | null;
    created_at: string | null;
  }>;
  available_actions: string[];
};

export default function UserControlPage() {
  const [email, setEmail] = useState("");
  const [reason, setReason] = useState("Owner account access recovery");
  const [payload, setPayload] = useState<UserControlPayload | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [resetLink, setResetLink] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function lookup() {
    setLoading(true);
    setMessage(null);
    setResetLink(null);
    try {
      const response = await fetch(`/api/internal/ops/user-control?email=${encodeURIComponent(email)}`, { cache: "no-store" });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || data.error || "User lookup failed.");
        return;
      }
      setPayload(data);
    } finally {
      setLoading(false);
    }
  }

  async function runAction(action: "reset_link" | "revoke_invites") {
    setLoading(true);
    setMessage(null);
    setResetLink(null);
    try {
      const response = await fetch("/api/internal/ops/user-control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, email, reason }),
      });
      const data = await response.json();
      if (!response.ok) {
        setMessage(data.detail || data.error || "Action failed.");
        return;
      }
      if (data.reset_path) {
        setResetLink(`${window.location.origin}${data.reset_path}`);
        setMessage(`Reset link generated. Token TTL: ${data.token_ttl_hours} hours.`);
      } else {
        setMessage(`${data.status}. Count: ${data.revoked_count ?? 0}`);
      }
      await lookup();
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
      <section className="mx-auto max-w-6xl px-5 py-8 md:px-8">
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.3em] text-[#8a6a34]">VoxaRisk Internal</p>
            <h1 className="mt-2 text-3xl font-black">Owner User Control</h1>
            <p className="mt-2 max-w-3xl text-sm text-neutral-700">
              Controlled account recovery and invite hygiene. No hard-delete, no Stripe changes, no public workflow changes.
            </p>
          </div>
          <Link href="/internal/operations" className="rounded-xl border border-[#d8c49e] px-4 py-2 text-sm font-semibold text-[#6f5328] hover:bg-[#fbf5ea]">
            Back to operations
          </Link>
        </div>

        <div className="rounded-3xl border border-[#d8c49e] bg-white p-5 shadow-sm">
          <label className="text-sm font-bold text-neutral-800">Search user by email</label>
          <div className="mt-3 flex flex-col gap-3 md:flex-row">
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="user@example.com"
              className="flex-1 rounded-xl border border-[#d8c49e] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]"
            />
            <button
              onClick={lookup}
              disabled={loading || !email}
              className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-bold text-stone-100 disabled:opacity-50"
            >
              {loading ? "Working..." : "Find user"}
            </button>
          </div>

          <label className="mt-5 block text-sm font-bold text-neutral-800">Operator reason</label>
          <input
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            className="mt-2 w-full rounded-xl border border-[#d8c49e] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]"
          />

          {message && (
            <div className="mt-4 rounded-xl border border-[#d8c49e] bg-[#fff8ea] p-4 text-sm font-semibold text-[#6f5328]">
              {message}
            </div>
          )}

          {resetLink && (
            <div className="mt-4 rounded-xl border border-emerald-300 bg-emerald-50 p-4">
              <p className="text-sm font-bold text-emerald-900">Generated reset/setup link</p>
              <input readOnly value={resetLink} className="mt-2 w-full rounded-lg border border-emerald-300 px-3 py-2 text-sm" />
            </div>
          )}
        </div>

        {payload && (
          <div className="mt-6 rounded-3xl border border-[#d8c49e] bg-white p-5 shadow-sm">
            <div className="flex flex-col justify-between gap-4 border-b border-[#eadcc2] pb-4 md:flex-row">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.2em] text-[#8a6a34]">Target user</p>
                <h2 className="mt-1 text-2xl font-black">{payload.email}</h2>
                <p className="mt-1 text-sm text-neutral-600">{payload.found ? "User account found." : "No user account found."}</p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => runAction("reset_link")}
                  disabled={loading || !payload.available_actions.includes("generate_reset_link")}
                  className="rounded-xl bg-[#11110f] px-4 py-2 text-sm font-bold text-white disabled:opacity-40"
                >
                  Generate reset/setup link
                </button>
                <button
                  onClick={() => runAction("revoke_invites")}
                  disabled={loading || !payload.available_actions.includes("revoke_pending_invites")}
                  className="rounded-xl border border-red-300 bg-red-50 px-4 py-2 text-sm font-bold text-red-900 disabled:opacity-40"
                >
                  Revoke pending invites
                </button>
              </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-[#eadcc2] p-4">
                <h3 className="font-bold">Account</h3>
                {payload.user ? (
                  <dl className="mt-3 space-y-2 text-sm">
                    <div><dt className="font-semibold">User ID</dt><dd className="break-all text-neutral-700">{payload.user.id}</dd></div>
                    <div><dt className="font-semibold">Role</dt><dd>{payload.user.role}</dd></div>
                    <div><dt className="font-semibold">Active</dt><dd>{payload.user.is_active ? "Yes" : "No"}</dd></div>
                    <div><dt className="font-semibold">Primary org</dt><dd className="break-all text-neutral-700">{payload.user.org_id}</dd></div>
                  </dl>
                ) : <p className="mt-3 text-sm text-neutral-600">No account exists for this email.</p>}
              </div>

              <div className="rounded-2xl border border-[#eadcc2] p-4">
                <h3 className="font-bold">Memberships</h3>
                <div className="mt-3 space-y-3 text-sm">
                  {payload.memberships.length ? payload.memberships.map((membership) => (
                    <div key={membership.id} className="rounded-xl bg-[#fbf5ea] p-3">
                      <p className="font-semibold">{membership.organization_name || membership.org_id}</p>
                      <p>Role: {membership.role} / Status: {membership.status}</p>
                    </div>
                  )) : <p className="text-neutral-600">No memberships found.</p>}
                </div>
              </div>

              <div className="rounded-2xl border border-[#eadcc2] p-4">
                <h3 className="font-bold">Invites</h3>
                <div className="mt-3 space-y-3 text-sm">
                  {payload.invites.length ? payload.invites.map((invite) => (
                    <div key={invite.id} className="rounded-xl bg-[#fbf5ea] p-3">
                      <p>Status: <strong>{invite.status}</strong> / Role: {invite.role}</p>
                      <p className="text-neutral-600">Expires: {invite.expires_at || "n/a"}</p>
                    </div>
                  )) : <p className="text-neutral-600">No invites found.</p>}
                </div>
              </div>

              <div className="rounded-2xl border border-[#eadcc2] p-4">
                <h3 className="font-bold">Password/reset tokens</h3>
                <div className="mt-3 space-y-3 text-sm">
                  {payload.password_tokens.length ? payload.password_tokens.map((token) => (
                    <div key={token.id} className="rounded-xl bg-[#fbf5ea] p-3">
                      <p>Purpose: {token.purpose} / Status: <strong>{token.status}</strong></p>
                      <p className="text-neutral-600">Expires: {token.expires_at || "n/a"}</p>
                    </div>
                  )) : <p className="text-neutral-600">No password tokens found.</p>}
                </div>
              </div>
            </div>

            <div className="mt-5 rounded-2xl border border-[#eadcc2] bg-[#fff8ea] p-4 text-sm text-[#6f5328]">
              Deferred deliberately: hard delete, billing edits, Stripe controls, and broad dashboard rebuild.
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
