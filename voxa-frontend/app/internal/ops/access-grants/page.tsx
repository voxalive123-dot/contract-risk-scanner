"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import SiteFooter from "../../../site-footer";

type GrantRow = {
  id: string;
  email: string | null;
  user_id: string | null;
  organization_id: string;
  organization_name: string | null;
  granted_plan: "executive" | "enterprise";
  grant_type: string;
  scan_quota_override: number | null;
  reason: string;
  starts_at: string | null;
  expires_at: string | null;
  status: string;
  effective_active: boolean;
  created_by_email: string | null;
  created_at: string | null;
  revoked_at: string | null;
  revocation_reason: string | null;
};

type GrantListPayload = {
  read_only: boolean;
  grants: GrantRow[];
};

type GrantCreatePayload = {
  status: "granted_existing_account" | "needs_account_setup";
  grant: GrantRow;
  setup_token: string | null;
};

type DurationOption = "10" | "14" | "30" | "custom";

function formatDateTime(value: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(parsed);
}

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
          <Link href="/internal/operations" className="rounded-xl border border-[#d8c49e] px-4 py-2 font-semibold text-[#6f5328] transition hover:bg-[#fbf5ea]">
            Operations
          </Link>
          <Link href="/account" className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
            Account
          </Link>
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

function statusTone(grant: GrantRow) {
  if (!grant.effective_active || grant.status !== "active") {
    return "border-red-300 bg-red-50 text-red-900";
  }
  return "border-emerald-300 bg-emerald-50 text-emerald-900";
}

export default function InternalAccessGrantsPage() {
  const [grants, setGrants] = useState<GrantRow[]>([]);
  const [pageMessage, setPageMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<GrantCreatePayload | null>(null);
  const [revokeBusyId, setRevokeBusyId] = useState<string | null>(null);
  const [revokeReasons, setRevokeReasons] = useState<Record<string, string>>({});

  const [email, setEmail] = useState("");
  const [grantedPlan, setGrantedPlan] = useState<"executive" | "enterprise">("executive");
  const [durationOption, setDurationOption] = useState<DurationOption>("14");
  const [customDays, setCustomDays] = useState("10");
  const [scanQuotaOverride, setScanQuotaOverride] = useState("");
  const [reason, setReason] = useState("family_beta_testing");

  const resolvedDurationDays = useMemo(() => {
    if (durationOption === "custom") {
      const parsed = Number.parseInt(customDays, 10);
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
    }
    return Number.parseInt(durationOption, 10);
  }, [customDays, durationOption]);

  async function loadGrants() {
    const response = await fetch("/api/internal/ops/access-grants", { cache: "no-store" });
    if (!response.ok) {
      throw new Error("access_grants_unavailable");
    }
    const data: GrantListPayload = await response.json();
    setGrants(data.grants ?? []);
  }

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        await loadGrants();
      } catch {
        if (!cancelled) {
          setPageMessage("Internal access grants are unavailable for this account.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleGrantAccess(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPageMessage(null);
    setSubmitResult(null);
    setIsSubmitting(true);

    try {
      const payload = {
        email,
        granted_plan: grantedPlan,
        duration_days: resolvedDurationDays,
        scan_quota_override: scanQuotaOverride ? Number.parseInt(scanQuotaOverride, 10) : null,
        reason,
      };

      const response = await fetch("/api/internal/ops/access-grants", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || data?.error || "Access grant could not be created.");
      }

      setSubmitResult(data);
      setEmail("");
      setScanQuotaOverride("");
      setReason("family_beta_testing");
      setDurationOption(grantedPlan === "enterprise" ? "30" : "14");
      setCustomDays("10");
      await loadGrants();
    } catch (error) {
      setPageMessage(error instanceof Error ? error.message : "Access grant could not be created.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleRevoke(grantId: string) {
    const revokeReason = (revokeReasons[grantId] || "").trim();
    if (revokeReason.length < 8) {
      setPageMessage("A clear revocation reason is required.");
      return;
    }

    setPageMessage(null);
    setRevokeBusyId(grantId);
    try {
      const response = await fetch(`/api/internal/ops/access-grants/${encodeURIComponent(grantId)}/revoke`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reason: revokeReason }),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.detail || data?.error || "Grant could not be revoked.");
      }
      setRevokeReasons((current) => ({ ...current, [grantId]: "" }));
      await loadGrants();
    } catch (error) {
      setPageMessage(error instanceof Error ? error.message : "Grant could not be revoked.");
    } finally {
      setRevokeBusyId(null);
    }
  }

  const setupUrl =
    submitResult?.status === "needs_account_setup" && submitResult.setup_token
      ? `${typeof window !== "undefined" ? window.location.origin : ""}/account/setup?token=${encodeURIComponent(submitResult.setup_token)}`
      : null;

  return (
    <main className="min-h-screen bg-[#f3ecdf] text-neutral-950">
      <SiteHeader />

      <section className="border-b border-[#e4d6be] bg-[#f7f1e6]">
        <div className="mx-auto grid max-w-[1360px] gap-8 px-5 py-12 md:px-8 lg:grid-cols-[minmax(0,1.15fr)_minmax(340px,0.85fr)] lg:items-start">
          <div className="space-y-4">
            <Eyebrow>Tester Access Grants</Eyebrow>
            <h1 className="max-w-3xl text-4xl font-semibold tracking-[-0.03em] text-neutral-950 md:text-5xl">
              Grant temporary Executive or Enterprise access safely.
            </h1>
            <p className="max-w-2xl text-[17px] leading-8 text-neutral-700">
              This internal owner workflow creates time-limited entitlement grants for family and beta testers without
              bypassing the main Stripe-backed entitlement model.
            </p>
          </div>

          <div className="rounded-[28px] border border-[#dcc9a6] bg-[#fffaf1] p-6 shadow-[0_18px_50px_rgba(77,55,24,0.08)]">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">Guardrails</div>
            <div className="mt-4 space-y-3 text-sm leading-6 text-neutral-700">
              <p>Use grants for temporary evaluation only. Expired or revoked grants stop applying automatically.</p>
              <p>New emails use the existing secure account setup token flow. No plain-text password is generated or stored.</p>
              <p>Stripe subscriptions remain the normal paid source of truth for customer access.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-5 py-10 md:px-8">
        <div className="grid gap-8 xl:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
          <div className="rounded-[28px] border border-[#dcc9a6] bg-[#fffaf1] p-7 shadow-[0_18px_50px_rgba(77,55,24,0.06)]">
            <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">New grant</div>
            <h2 className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-neutral-950">Create tester access</h2>
            <p className="mt-2 text-sm leading-6 text-neutral-700">
              Existing users are granted immediately. New emails receive a secure setup link and the grant applies after password setup.
            </p>

            <form className="mt-6 space-y-5" onSubmit={handleGrantAccess}>
              <label className="block text-sm font-medium text-neutral-800">
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="tester@example.com"
                  required
                  className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                />
              </label>

              <div className="grid gap-4 md:grid-cols-2">
                <label className="block text-sm font-medium text-neutral-800">
                  Plan
                  <select
                    value={grantedPlan}
                    onChange={(event) => {
                      const nextPlan = event.target.value as "executive" | "enterprise";
                      setGrantedPlan(nextPlan);
                      setDurationOption(nextPlan === "enterprise" ? "30" : "14");
                    }}
                    className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                  >
                    <option value="executive">Executive</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </label>

                <label className="block text-sm font-medium text-neutral-800">
                  Duration
                  <select
                    value={durationOption}
                    onChange={(event) => setDurationOption(event.target.value as DurationOption)}
                    className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                  >
                    <option value="10">10 days</option>
                    <option value="14">14 days</option>
                    <option value="30">30 days</option>
                    <option value="custom">Custom</option>
                  </select>
                </label>
              </div>

              {durationOption === "custom" ? (
                <label className="block text-sm font-medium text-neutral-800">
                  Custom duration (days)
                  <input
                    type="number"
                    min={1}
                    max={365}
                    value={customDays}
                    onChange={(event) => setCustomDays(event.target.value)}
                    className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                  />
                </label>
              ) : null}

              <label className="block text-sm font-medium text-neutral-800">
                Optional scan quota override
                <input
                  type="number"
                  min={1}
                  value={scanQuotaOverride}
                  onChange={(event) => setScanQuotaOverride(event.target.value)}
                  placeholder="Leave blank to use plan default"
                  className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                />
              </label>

              <label className="block text-sm font-medium text-neutral-800">
                Reason / note
                <input
                  type="text"
                  value={reason}
                  onChange={(event) => setReason(event.target.value)}
                  required
                  className="mt-2 w-full rounded-2xl border border-[#d8c49e] bg-white px-4 py-3 text-[15px] text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                />
              </label>

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center rounded-2xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? "Granting access..." : "Grant access"}
              </button>
            </form>

            {pageMessage ? (
              <div className="mt-5 rounded-2xl border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-900">{pageMessage}</div>
            ) : null}
          </div>

          <div className="space-y-5">
            <div className="rounded-[28px] border border-[#dcc9a6] bg-[#fffaf1] p-7 shadow-[0_18px_50px_rgba(77,55,24,0.06)]">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">Latest result</div>
              <h2 className="mt-3 text-2xl font-semibold tracking-[-0.02em] text-neutral-950">Grant confirmation</h2>
              <p className="mt-2 text-sm leading-6 text-neutral-700">
                After creation, the grant appears immediately in the active list below. New-user grants also surface the secure setup link here.
              </p>

              {submitResult ? (
                <div className="mt-5 rounded-3xl border border-[#d8c49e] bg-white px-5 py-5 shadow-sm">
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${statusTone(submitResult.grant)}`}>
                      {submitResult.status === "needs_account_setup" ? "Setup pending" : "Grant active"}
                    </span>
                    <span className="text-sm text-neutral-700">
                      {submitResult.grant.granted_plan.charAt(0).toUpperCase() + submitResult.grant.granted_plan.slice(1)} access for{" "}
                      <span className="font-semibold text-neutral-950">{submitResult.grant.email || "tester account"}</span>
                    </span>
                  </div>
                  <dl className="mt-4 grid gap-3 text-sm text-neutral-700 md:grid-cols-2">
                    <div>
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">Organisation</dt>
                      <dd className="mt-1 font-medium text-neutral-950">{submitResult.grant.organization_name || "VoxaRisk Platform"}</dd>
                    </div>
                    <div>
                      <dt className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">Expires</dt>
                      <dd className="mt-1 font-medium text-neutral-950">{formatDateTime(submitResult.grant.expires_at)}</dd>
                    </div>
                  </dl>
                  {setupUrl ? (
                    <div className="mt-4 rounded-2xl border border-[#d8c49e] bg-[#f9f4ea] px-4 py-4 text-sm text-neutral-800">
                      <div className="font-semibold text-neutral-950">Secure setup link created</div>
                      <div className="mt-2 break-all text-[13px] leading-6 text-neutral-700">{setupUrl}</div>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="mt-5 rounded-3xl border border-dashed border-[#d8c49e] bg-[#fcf8f0] px-5 py-8 text-sm text-neutral-600">
                  No new grant created in this session yet.
                </div>
              )}
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-5 pb-16 md:px-8">
        <div className="rounded-[32px] border border-[#dcc9a6] bg-[#fffaf1] p-7 shadow-[0_18px_50px_rgba(77,55,24,0.06)]">
          <div className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">Active grants</div>
              <h2 className="mt-3 text-3xl font-semibold tracking-[-0.03em] text-neutral-950">Current tester access</h2>
            </div>
            <div className="text-sm text-neutral-600">{isLoading ? "Loading grants..." : `${grants.length} active grant${grants.length === 1 ? "" : "s"}`}</div>
          </div>

          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full border-separate border-spacing-0 text-left text-sm text-neutral-800">
              <thead>
                <tr className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
                  <th className="border-b border-[#eadfc8] px-4 py-3">Email</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Organisation / account</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Plan</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Grant detail</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Starts</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Expires</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Status</th>
                  <th className="border-b border-[#eadfc8] px-4 py-3">Revoke</th>
                </tr>
              </thead>
              <tbody>
                {grants.map((grant) => (
                  <tr key={grant.id} className="align-top">
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <div className="font-medium text-neutral-950">{grant.email || "Pending setup"}</div>
                      <div className="mt-1 text-xs text-neutral-500">{grant.user_id ? "Existing account" : "Setup pending"}</div>
                    </td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <div className="font-medium text-neutral-950">{grant.organization_name || "VoxaRisk Platform"}</div>
                      <div className="mt-1 text-xs text-neutral-500">{grant.organization_id}</div>
                    </td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <div className="font-medium capitalize text-neutral-950">{grant.granted_plan}</div>
                      {grant.scan_quota_override ? <div className="mt-1 text-xs text-neutral-500">Override: {grant.scan_quota_override}</div> : null}
                    </td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <div className="font-medium text-neutral-950">{grant.reason}</div>
                      <div className="mt-1 text-xs text-neutral-500">{grant.grant_type}</div>
                    </td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4 text-neutral-700">{formatDateTime(grant.starts_at)}</td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4 text-neutral-700">{formatDateTime(grant.expires_at)}</td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${statusTone(grant)}`}>
                        {grant.effective_active ? "Active" : grant.status}
                      </span>
                    </td>
                    <td className="border-b border-[#f0e7d7] px-4 py-4">
                      <div className="space-y-3">
                        <input
                          type="text"
                          value={revokeReasons[grant.id] ?? ""}
                          onChange={(event) =>
                            setRevokeReasons((current) => ({
                              ...current,
                              [grant.id]: event.target.value,
                            }))
                          }
                          placeholder="revocation reason"
                          className="w-full min-w-[220px] rounded-2xl border border-[#d8c49e] bg-white px-3 py-2 text-sm text-neutral-900 shadow-sm outline-none transition focus:border-[#b08d57] focus:ring-2 focus:ring-[#e5d1a8]"
                        />
                        <button
                          type="button"
                          onClick={() => void handleRevoke(grant.id)}
                          disabled={revokeBusyId === grant.id}
                          className="inline-flex items-center rounded-2xl border border-red-300 px-4 py-2 text-sm font-semibold text-red-900 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60"
                        >
                          {revokeBusyId === grant.id ? "Revoking..." : "Revoke"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!isLoading && grants.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-10 text-center text-sm text-neutral-600">
                      No active grants found.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <SiteFooter />
    </main>
  );
}
