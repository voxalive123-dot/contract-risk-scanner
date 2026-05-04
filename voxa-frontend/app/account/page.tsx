"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AccountShell, Metric, Panel, formatAccountDateTime } from "./account-ui";

type Summary = {
  user: { email: string; account_status: string };
  organization: { id: string; name: string };
  membership: { role: string; status: string };
  entitlement: { effective_plan: string; subscription_state: string; monthly_scan_limit: number; paid_access: boolean; source: string };
  usage: { monthly_scans_used: number; monthly_scan_limit: number; scan_limit_remaining: number; total_scans: number; latest_scan_at: string | null };
  subscription: { plan_name: string; status: string; current_period_end: string | null; source: string };
  profile: { legal_identity_complete: boolean; display_name?: string | null };
};

export default function AccountOverviewPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [message, setMessage] = useState("Loading account dashboard...");

  useEffect(() => {
    fetch("/api/account/summary", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("account_unavailable");
        return response.json();
      })
      .then((data) => { setSummary(data); setMessage(""); })
      .catch(() => setMessage("Sign in is required to view the account dashboard."));
  }, []);

  return (
    <AccountShell eyebrow="Customer account" title="Account control surface.">
      {message && <div className="mt-8 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
      {summary && (
        <div className="mt-8 space-y-6">
          <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            <Metric label="Plan" value={summary.entitlement.effective_plan} detail={summary.entitlement.source} />
            <Metric label="Subscription" value={summary.subscription.status} detail={summary.subscription.source} />
            <Metric label="Usage" value={`${summary.usage.monthly_scans_used}/${summary.usage.monthly_scan_limit}`} detail="Current monthly scan usage" />
            <Metric label="Remaining" value={summary.usage.scan_limit_remaining} />
            <Metric label="Account" value={summary.user.account_status} detail={summary.membership.status} />
            <Metric label="Scans" value={summary.usage.total_scans} detail={summary.usage.latest_scan_at ? formatAccountDateTime(summary.usage.latest_scan_at) : "No scans yet"} />
          </div>
          <div className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
            <Panel title="Identity and organisation">
              <div className="mt-5 space-y-3 text-sm leading-6 text-neutral-700">
                <div><span className="font-semibold text-neutral-950">Email:</span> {summary.user.email}</div>
                <div><span className="font-semibold text-neutral-950">Organisation:</span> {summary.organization.name}</div>
                <div><span className="font-semibold text-neutral-950">Role:</span> {summary.membership.role}</div>
                <div><span className="font-semibold text-neutral-950">Legal identity:</span> {summary.profile.legal_identity_complete ? "Complete" : "Required"}</div>
              </div>
            </Panel>
            <Panel title="Work areas">
              <div className="mt-5 grid gap-3 md:grid-cols-2">
                {[
                  ["Historical scans", "/account/scans", "Review prior contract reports and decision history."],
                  ["Billing and invoices", "/account/billing", "Open Stripe billing and view stored invoice records."],
                  ["Profile", "/account/profile", "Maintain legal, business, and display identity layers."],
                  ["Security", "/account/security", "Change password or request controlled closure."],
                ].map(([label, href, detail]) => (
                  <Link key={href} href={href} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 transition hover:bg-[#fff8ea]"><div className="font-semibold text-neutral-950">{label}</div><div className="mt-2 text-xs leading-5 text-neutral-600">{detail}</div></Link>
                ))}
              </div>
            </Panel>
          </div>
        </div>
      )}
    </AccountShell>
  );
}
