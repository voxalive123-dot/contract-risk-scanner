"use client";

import { useEffect, useState } from "react";
import { AccountShell, Metric, Panel } from "../account-ui";

type Invoice = { id: string; date: string | null; amount_paid: number | null; amount_due: number | null; currency: string | null; status: string; hosted_invoice_url: string | null; invoice_pdf: string | null };
type Summary = { subscription: { plan_name: string; status: string; current_period_end: string | null }; billing: { invoices: Invoice[]; invoice_storage_status: string } };

export default function BillingPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [message, setMessage] = useState("Loading billing...");
  const [opening, setOpening] = useState(false);

  useEffect(() => { fetch("/api/account/summary", { cache: "no-store" }).then(async (r) => { if (!r.ok) throw new Error(); return r.json(); }).then((data) => { setSummary(data); setMessage(""); }).catch(() => setMessage("Billing is unavailable for this account.")); }, []);

  async function openPortal() {
    setOpening(true);
    const response = await fetch("/api/account/billing/portal", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ return_url: `${window.location.origin}/account/billing` }) });
    const payload = await response.json().catch(() => null);
    setOpening(false);
    if (response.ok && payload?.url) window.location.href = payload.url;
    else setMessage("Stripe billing portal is not available for this organisation yet.");
  }

  return <AccountShell eyebrow="Billing" title="Billing and invoices.">
    {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
    {summary && <div className="mt-6 space-y-6"><div className="grid gap-4 md:grid-cols-3"><Metric label="Plan" value={summary.subscription.plan_name} /><Metric label="Status" value={summary.subscription.status} /><Metric label="Period end" value={summary.subscription.current_period_end ?? "?"} /></div><Panel title="Stripe billing portal"><p className="mt-4 text-sm leading-7 text-neutral-700">Payment method and subscription changes are handled through the existing Stripe billing portal.</p><button type="button" onClick={openPortal} disabled={opening} className="mt-5 rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 disabled:opacity-60">{opening ? "Opening..." : "Manage billing"}</button></Panel><Panel title="Stored invoices"><div className="mt-4 text-xs uppercase tracking-[0.16em] text-[#8a6a34]">{summary.billing.invoice_storage_status}</div><div className="mt-4 space-y-3">{summary.billing.invoices.length === 0 && <div className="text-sm text-neutral-600">No invoice records have been stored from Stripe webhooks yet.</div>}{summary.billing.invoices.map((invoice) => <div key={invoice.id} className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-sm text-neutral-700"><div className="font-semibold text-neutral-950">{invoice.date ?? "Invoice"} / {invoice.status}</div><div className="mt-1">Paid: {invoice.amount_paid ?? "?"} {invoice.currency ?? ""}</div><div className="mt-2 flex gap-4">{invoice.hosted_invoice_url && <a className="font-semibold text-[#6f5328] underline" href={invoice.hosted_invoice_url}>Open invoice</a>}{invoice.invoice_pdf && <a className="font-semibold text-[#6f5328] underline" href={invoice.invoice_pdf}>PDF</a>}</div></div>)}</div></Panel></div>}
  </AccountShell>;
}
