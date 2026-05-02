"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";
import SiteFooter from "../site-footer";

export type BlockedReason = "signin" | "restricted" | null;

export type TableColumn<T> = {
  key: string;
  label: string;
  className?: string;
  render: (row: T) => ReactNode;
};

const internalNav = [
  ["Command", "/internal/command-centre"],
  ["Users", "/internal/users"],
  ["Orgs", "/internal/orgs"],
  ["Subscriptions", "/internal/subscriptions"],
  ["Revenue", "/internal/revenue"],
  ["Scans", "/internal/scans"],
  ["Audit", "/internal/audit"],
  ["Staff", "/internal/staff"],
];

export const OWNER_SIGNIN_HREF = "/signin?next=/internal/command-centre";
export const PLATFORM_OWNER_EMAIL = "admin.dashboard@voxarisk.com";

export function blockedReasonFromStatus(status: number): BlockedReason {
  if (status === 401) return "signin";
  if (status === 403) return "restricted";
  return "signin";
}

export function formatDate(value?: string | null) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function formatMoneyMinor(value?: number | null, currency = "GBP") {
  if (!value) return "No stored revenue";
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(value / 100);
}

export function readable(value?: string | null) {
  if (!value) return "-";
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

export function InternalShell({ title, eyebrow, subtitle, children }: { title: string; eyebrow: string; subtitle?: string; children: ReactNode }) {
  const pathname = usePathname();

  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
          <div className="mx-auto flex max-w-[1440px] flex-col gap-5 px-5 py-5 md:px-8 xl:flex-row xl:items-center xl:justify-between">
            <Link href="/internal/command-centre" className="flex items-center gap-4">
              <div className="flex h-[72px] w-[72px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
                <Image src="/brand/voxa-circle-logo.png" alt="VOXA" width={72} height={72} className="h-full w-full rounded-full object-cover object-center" priority />
              </div>
              <div>
                <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">VOXARISK</div>
                <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b5d2c]">OWNER COMMAND CENTRE</div>
              </div>
            </Link>
            <nav className="flex flex-wrap gap-2 text-sm" aria-label="Internal command centre">
              {internalNav.map(([label, href]) => {
                const active = pathname === href;
                return (
                  <Link
                    key={href}
                    href={href}
                    className={`rounded-xl border px-4 py-2 font-semibold transition ${
                      active
                        ? "border-[#11110f] bg-[#11110f] text-stone-100 shadow-[0_10px_24px_rgba(17,17,15,0.18)]"
                        : "border-[#d8c49e] bg-[#fff8ea] text-[#6f5328] hover:bg-[#f3e4c6]"
                    }`}
                  >
                    {label}
                  </Link>
                );
              })}
            </nav>
          </div>
        </header>
        <section className="mx-auto max-w-[1440px] px-5 py-8 md:px-8 md:py-10">
          <div className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-6 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-9">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]"><span className="h-px w-8 bg-[#b08d57]" />{eyebrow}</div>
                <h1 className="mt-4 max-w-5xl text-3xl font-semibold leading-[1.08] text-neutral-950 md:text-5xl">{title}</h1>
                {subtitle && <p className="mt-4 max-w-4xl text-sm leading-7 text-neutral-700 md:text-base">{subtitle}</p>}
              </div>
              <div className="rounded-2xl border border-[#d8c49e] bg-[#fbf3e5] px-4 py-3 text-xs leading-5 text-[#6f5328]">
                <div className="font-bold uppercase tracking-[0.16em]">Protected owner surface</div>
                <div className="mt-1">Backend permission checks required</div>
              </div>
            </div>
            {children}
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

export function LoadingNotice({ label = "Loading command data..." }: { label?: string }) {
  return <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{label}</div>;
}

export function InternalBlockedState({ reason }: { reason: "signin" | "restricted" }) {
  const message = reason === "restricted"
    ? "This area is restricted to VoxaRisk owner/internal staff."
    : "Sign in with a VoxaRisk owner/internal account to open the command centre.";

  return (
    <section className="mt-6 rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
      <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Access required</div>
      <p className="mt-4 max-w-2xl text-sm leading-7 text-neutral-700">{message}</p>
      <Link href={OWNER_SIGNIN_HREF} className="mt-5 inline-flex rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
        Sign in as owner
      </Link>
    </section>
  );
}

export function MetricCard({ label, value, detail, tone = "neutral" }: { label: string; value: ReactNode; detail?: ReactNode; tone?: "neutral" | "good" | "warn" | "danger" }) {
  const accent = tone === "good" ? "border-emerald-300 bg-emerald-50" : tone === "warn" ? "border-amber-300 bg-amber-50" : tone === "danger" ? "border-rose-300 bg-rose-50" : "border-[#d8c49e] bg-[#fbf3e5]";
  return (
    <div className={`rounded-xl border p-4 ${accent}`}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">{label}</div>
      <div className="mt-2 text-2xl font-semibold text-neutral-950">{value}</div>
      {detail && <div className="mt-2 text-xs leading-5 text-neutral-600">{detail}</div>}
    </div>
  );
}

export const Metric = MetricCard;

export function Panel({ title, subtitle, action, children }: { title: string; subtitle?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-[1.25rem] border border-[#d8c49e] bg-[#fbf3e5] p-5 md:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">{title}</div>
          {subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-neutral-600">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}

export function StatusBadge({ value, tone }: { value?: string | null; tone?: "neutral" | "good" | "warn" | "danger" | "owner" }) {
  const normalized = (value ?? "unknown").toLowerCase();
  const resolved = tone ?? (normalized.includes("active") || normalized.includes("paid") || normalized.includes("owner_bypass") ? "good" : normalized.includes("suspend") || normalized.includes("past") || normalized.includes("trial") ? "warn" : normalized.includes("disable") || normalized.includes("restricted") || normalized.includes("unpaid") || normalized.includes("deleted") ? "danger" : "neutral");
  const classes = resolved === "owner"
    ? "border-[#11110f] bg-[#11110f] text-stone-100"
    : resolved === "good"
      ? "border-emerald-300 bg-emerald-50 text-emerald-800"
      : resolved === "warn"
        ? "border-amber-300 bg-amber-50 text-amber-800"
        : resolved === "danger"
          ? "border-rose-300 bg-rose-50 text-rose-800"
          : "border-[#d8c49e] bg-[#fff8ea] text-[#6f5328]";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.12em] ${classes}`}>{readable(value ?? "unknown")}</span>;
}

export function DataTable<T>({ columns, rows, emptyLabel }: { columns: TableColumn<T>[]; rows: T[]; emptyLabel: string }) {
  return (
    <div className="mt-5 overflow-x-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8]">
      <table className="min-w-full text-left text-xs text-neutral-700">
        <thead className="bg-[#f7ecd8] text-[11px] uppercase tracking-[0.16em] text-[#8a6a34]">
          <tr>{columns.map((column) => <th key={column.key} className={`px-3 py-3 align-top font-bold ${column.className ?? ""}`}>{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr><td colSpan={columns.length} className="px-4 py-8 text-center text-sm text-neutral-500">{emptyLabel}</td></tr>
          ) : rows.map((row, index) => (
            <tr key={index} className="border-t border-[#ead9bb] align-top">
              {columns.map((column) => <td key={column.key} className={`px-3 py-3 ${column.className ?? ""}`}>{column.render(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ActionButton({ children, onClick, disabled, tone = "neutral", title }: { children: ReactNode; onClick?: () => void; disabled?: boolean; tone?: "neutral" | "danger" | "primary"; title?: string }) {
  const classes = tone === "primary"
    ? "border-[#11110f] bg-[#11110f] text-stone-100 hover:bg-[#1b1a17]"
    : tone === "danger"
      ? "border-rose-300 bg-rose-50 text-rose-800 hover:bg-rose-100"
      : "border-[#d2bd96] bg-[#fffdf8] text-[#6f5328] hover:bg-[#f7ecd8]";
  return <button type="button" title={title} disabled={disabled} onClick={onClick} className={`rounded-lg border px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-45 ${classes}`}>{children}</button>;
}

export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="mt-5 rounded-xl border border-dashed border-[#d2bd96] bg-[#fffdf8] p-6">
      <div className="font-semibold text-neutral-950">{title}</div>
      <div className="mt-2 text-sm leading-6 text-neutral-600">{children}</div>
    </div>
  );
}

export function RawDataDisclosure({ data }: { data: unknown }) {
  return (
    <details className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-4">
      <summary className="cursor-pointer text-[11px] font-bold uppercase tracking-[0.18em] text-[#8a6a34]">Developer raw data</summary>
      <pre className="mt-4 max-h-[460px] overflow-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-xs leading-6 text-neutral-700">{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
