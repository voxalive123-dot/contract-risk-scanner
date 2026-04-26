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
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader activeItem={activeItem} />
        {children}
      </main>
      <SiteFooter />
    </>
  );
}

export function BoundaryNotice({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[1.15rem] border border-[#d9c7a6] bg-[#fbf3e5] px-5 py-4 text-sm leading-7 text-neutral-700">
      {children}
    </div>
  );
}

export function InsightArticleLayout({ article }: { article: InsightArticle }) {
  return (
    <InsightsShell activeItem="insights">
      <section className="mx-auto max-w-[1100px] px-6 py-10 md:px-8">
        <div className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <Eyebrow>{article.category}</Eyebrow>
          <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.08] tracking-[-0.05em] text-neutral-950 md:text-5xl">
            {article.title}
          </h1>
          <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">{article.summary}</p>
        </div>
      </section>

      <section className="mx-auto max-w-[1100px] px-6 pb-16 md:px-8">
        <article className="rounded-[1.75rem] border border-[#dfd0b6] bg-[#fffdf8] px-7 py-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)] md:px-10 md:py-10">
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

          <div className="mt-10 rounded-[1.35rem] border border-[#d8c49e] bg-[#fbf3e5] p-6">
            <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Structured first-pass review</div>
            <p className="mt-3 max-w-2xl text-sm leading-7 text-neutral-700">
              Use VoxaRisk to structure your first-pass review before escalation.
            </p>
            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/dashboard"
                className="rounded-xl bg-[#11110f] px-5 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
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
            <p className="mt-5 text-sm leading-7 text-neutral-700">
              VoxaRisk supports review discipline. It does not replace professional legal advice.
            </p>
          </div>
        </article>
      </section>
    </InsightsShell>
  );
}
