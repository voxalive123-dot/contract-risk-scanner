"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

export function formatAccountDateTime(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

export function AccountShell({ children, title, eyebrow }: { children: React.ReactNode; title: string; eyebrow: string }) {
  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader activeItem="account" authMode="authenticated" />
        <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
          <div className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-7 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
            <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
              <div>
                <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]"><span className="h-px w-8 bg-[#b08d57]" />{eyebrow}</div>
                <h1 className="mt-5 max-w-4xl text-4xl font-semibold leading-[1.05] text-neutral-950 md:text-5xl">{title}</h1>
              </div>
              <nav className="flex flex-wrap gap-2 text-sm">
                {[
                  ["Overview", "/account"],
                  ["Scans", "/account/scans"],
                  ["Billing", "/account/billing"],
                  ["Profile", "/account/profile"],
                  ["Security", "/account/security"],
                ].map(([label, href]) => (
                  <Link key={href} href={href} className="rounded-xl border border-[#d8c49e] bg-[#fff8ea] px-4 py-2 font-semibold text-[#6f5328] transition hover:bg-[#f3e4c6]">{label}</Link>
                ))}
              </nav>
            </div>
            {children}
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

export function Metric({ label, value, detail }: { label: string; value: React.ReactNode; detail?: string }) {
  return <div className="rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4"><div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">{label}</div><div className="mt-2 text-2xl font-semibold text-neutral-950">{value}</div>{detail && <div className="mt-2 text-xs leading-5 text-neutral-600">{detail}</div>}</div>;
}

export function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6"><div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">{title}</div>{children}</section>;
}

export type ToastItem = { id: number; message: string; type: "success" | "error" };
let _toastCounter = 0;

export function useToast() {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const showToast = useCallback((message: string, type: "success" | "error" = "success") => {
    const id = ++_toastCounter;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
  }, []);
  const dismissToast = useCallback((id: number) => setToasts((prev) => prev.filter((t) => t.id !== id)), []);
  return { toasts, showToast, dismissToast };
}

export function Toast({ toasts, onDismiss }: { toasts: ToastItem[]; onDismiss: (id: number) => void }) {
  if (toasts.length === 0) return null;
  return (
    <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div key={toast.id} className={`flex items-center gap-3 rounded-xl border px-4 py-3 text-sm font-semibold shadow-lg ${toast.type === "success" ? "border-emerald-300 bg-emerald-50 text-emerald-800" : "border-rose-300 bg-rose-50 text-rose-800"}`}>
          <span className="flex-1">{toast.message}</span>
          <button type="button" onClick={() => onDismiss(toast.id)} className="ml-1 text-xs opacity-60 hover:opacity-100" aria-label="Dismiss">✕</button>
        </div>
      ))}
    </div>
  );
}

export function ConfirmDialog({ open, title, description, requireReason = false, onConfirm, onCancel }: { open: boolean; title: string; description: string; requireReason?: boolean; onConfirm: (reason: string | null) => void; onCancel: () => void }) {
  const [reason, setReason] = useState("");
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md rounded-xl border border-[#d8c49e] bg-[#fffaf0] p-6 shadow-[0_22px_60px_rgba(75,55,25,0.22)]">
        <h2 className="text-base font-semibold text-neutral-950">{title}</h2>
        <p className="mt-3 text-sm leading-6 text-neutral-700">{description}</p>
        {requireReason && (
          <textarea value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason" className="mt-4 min-h-24 w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
        )}
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded-lg border border-[#d2bd96] bg-[#fffdf8] px-4 py-2 text-sm font-semibold text-[#6f5328] transition hover:bg-[#f3e4c6]">Cancel</button>
          <button type="button" onClick={() => onConfirm(requireReason ? reason : null)} disabled={requireReason && !reason.trim()} className="rounded-lg border border-red-300 bg-red-50 px-4 py-2 text-sm font-semibold text-red-900 transition hover:bg-red-100 disabled:opacity-45">Confirm</button>
        </div>
      </div>
    </div>
  );
}

export function Modal({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: React.ReactNode }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-2xl rounded-xl border border-[#d8c49e] bg-[#fffaf0] p-6 shadow-[0_22px_60px_rgba(75,55,25,0.22)]">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-base font-semibold text-neutral-950">{title}</h2>
          <button type="button" onClick={onClose} className="rounded-lg border border-[#d2bd96] bg-[#fffdf8] px-3 py-1.5 text-xs font-semibold text-[#6f5328] transition hover:bg-[#f3e4c6]">Close</button>
        </div>
        <div className="mt-5">{children}</div>
      </div>
    </div>
  );
}
