import Link from "next/link";

import { BoundaryNotice, InsightsShell } from "./insights-layout";
import { futureInsightTopics, insightArticles, InsightArticle } from "./insights-data";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

function InsightCard({ article }: { article: InsightArticle }) {
  return (
    <article className="rounded-[1.25rem] border border-[#e0d1b7] bg-[#fbf3e5] p-6">
      <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">{article.category}</div>
      <h3 className="mt-3 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">{article.title}</h3>
      <p className="mt-4 text-sm leading-7 text-neutral-700">{article.summary}</p>
      <div className="mt-6">
        <Link
          href={`/insights/${article.slug}`}
          className="inline-flex rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
        >
          Read insight
        </Link>
      </div>
    </article>
  );
}

const featuredArticles = insightArticles.filter((article) => article.collection === "featured");
const fundamentalsArticles = insightArticles.filter((article) => article.collection === "fundamentals");
const aiArticles = insightArticles.filter((article) => article.collection === "ai");
const preparationArticles = insightArticles.filter((article) => article.collection === "preparation");

export default function InsightsPage() {
  return (
    <InsightsShell activeItem="insights">
      <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
        <div className="grid gap-8 rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-stretch">
          <div className="flex flex-col justify-center">
            <Eyebrow>Public insights</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              Contract Risk Intelligence Insights
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              This section shares practical, non-legal-advice guidance on contract risk patterns, review discipline, and evidence-backed decision support for commercial users.
            </p>
          </div>

          <div className="flex h-full flex-col justify-center rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">Boundary</div>
            <p className="mt-5 text-sm leading-7 text-neutral-700">
              VoxaRisk provides contract risk intelligence and decision support, not legal advice.
            </p>
            <div className="mt-6">
              <Link
                href="/dashboard"
                className="inline-flex rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
              >
                Scan a contract
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-6 pb-8 md:px-8">
        <BoundaryNotice>
          VoxaRisk provides contract risk intelligence and decision support, not legal advice.
        </BoundaryNotice>
      </section>

      <section className="mx-auto max-w-[1360px] px-6 pb-16 md:px-8">
        <div className="grid gap-8">
          <section className="rounded-[1.75rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>Featured insights</Eyebrow>
            <div className="mt-6 grid gap-5 xl:grid-cols-2">
              {featuredArticles.map((article) => (
                <InsightCard key={article.slug} article={article} />
              ))}
            </div>
          </section>

          <section className="rounded-[1.75rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>Contract risk fundamentals</Eyebrow>
            <div className="mt-6 grid gap-5 xl:grid-cols-2">
              {fundamentalsArticles.map((article) => (
                <InsightCard key={article.slug} article={article} />
              ))}
            </div>
          </section>

          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_340px]">
            <section className="rounded-[1.75rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
              <Eyebrow>AI and review discipline</Eyebrow>
              <div className="mt-6 grid gap-5">
                {aiArticles.map((article) => (
                  <InsightCard key={article.slug} article={article} />
                ))}
              </div>
            </section>

            <aside className="rounded-[1.75rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
              <Eyebrow>Review preparation</Eyebrow>
              <div className="mt-6 grid gap-5">
                {preparationArticles.map((article) => (
                  <InsightCard key={article.slug} article={article} />
                ))}
              </div>

              <div className="mt-8 border-t border-[#eadfcd] pt-8">
                <Eyebrow>Coming next</Eyebrow>
                <div className="mt-6 grid gap-3">
                  {futureInsightTopics.map((topic) => (
                    <div key={topic} className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] px-4 py-4 text-sm leading-6 text-neutral-700">
                      {topic}
                    </div>
                  ))}
                </div>
              </div>
            </aside>
          </div>
        </div>
      </section>
    </InsightsShell>
  );
}
