import Link from "next/link";

import SiteFooter from "../site-footer";
import SiteHeader from "../site-header";
import { InsightArticle } from "./insights-data";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

export function InsightsShell({
  children,
  activeItem = "insights",
}: {
  children: React.ReactNode;
  activeItem?: "insights" | "product" | "pricing";
}) {
  return (
    <>
      <main className="min-h-screen bg-[#F5F1EB] text-neutral-950">
        <SiteHeader activeItem={activeItem} />
        {children}
      </main>
      <SiteFooter />
    </>
  );
}

export function BoundaryNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[1.15rem] border border-[rgba(198,168,107,0.22)] bg-[#eee6d8] px-5 py-4 text-sm leading-7 text-neutral-700">
      {children}
    </div>
  );
}

export function InsightArticleLayout({ article }: { article: InsightArticle }) {
  return (
    <InsightsShell activeItem="insights">
      <section className="mx-auto max-w-[1100px] px-6 py-10 md:px-8">
        <div className="rounded-[2rem] border border-[rgba(198,168,107,0.24)] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <Eyebrow>{article.category}</Eyebrow>
            {article.readingTime ? <span className="text-xs font-semibold uppercase tracking-[0.18em] text-neutral-500">{article.readingTime}</span> : null}
          </div>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.08] tracking-[-0.05em] text-neutral-950 md:text-5xl">
            {article.title}
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">{article.summary}</p>
        </div>
      </section>

      <section className="mx-auto max-w-[1100px] px-6 pb-16 md:px-8">
        <article className="rounded-[1.75rem] border border-[rgba(198,168,107,0.22)] bg-[#fffaf0] px-7 py-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)] md:px-10 md:py-10">
          <div className="space-y-10">
            {article.sections.map((section) => (
              <section key={section.heading} className="border-b border-[#eadfcd] pb-8 last:border-b-0 last:pb-0">
                <h2 className="text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">{section.heading}</h2>
                <div className="mt-4 space-y-4">
                  {section.paragraphs.map((paragraph) => (
                    <p key={paragraph} className="text-[15px] leading-8 text-neutral-700">
                      {paragraph}
                    </p>
                  ))}
                </div>
              </section>
            ))}
          </div>

          <div className="mt-10 rounded-[1.35rem] border border-[rgba(198,168,107,0.28)] bg-[#241C16] text-[#EDE7DF] p-6">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">Structured first-pass review</div>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-[#BFAE94]">
              Use VoxaRisk as an evidence-led decision-support layer for structured contract risk review and escalation discipline.
            </p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/dashboard"
                className="rounded-xl bg-[#1E1712] px-5 py-3 text-center text-sm font-semibold text-[#EDE7DF] transition hover:bg-[#322720]"
              >
                Scan a contract
              </Link>
              <Link
                href="/insights"
                className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-5 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]"
              >
                Back to Insights
              </Link>
            </div>
            {article.relatedLinks?.length ? (
              <div className="mt-5 flex flex-wrap gap-3">
                {article.relatedLinks.map((link) => (
                  <Link
                    key={link.href}
                    href={link.href}
                    className="rounded-xl border border-[#d8c49e] bg-[#fffdf8] px-4 py-2 text-sm font-semibold text-neutral-800 transition hover:bg-[#f3e4c6]"
                  >
                    {link.label}
                  </Link>
                ))}
              </div>
            ) : null}
            <p className="mt-5 text-sm leading-7 text-[#BFAE94]">
              VoxaRisk supports commercial risk intelligence and review discipline. It is not a substitute for professional legal advice, legal opinions, solicitor services, or contract approval.
            </p>
          </div>
        </article>
      </section>
    </InsightsShell>
  );
}
