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
