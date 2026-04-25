import SiteHeader from "./site-header";
import SiteFooter from "./site-footer";

type LegalSection = {
  title: string;
  body: string[];
};

type LegalPageProps = {
  eyebrow: string;
  title: string;
  intro: string;
  sections: LegalSection[];
};

export default function LegalPage({ eyebrow, title, intro, sections }: LegalPageProps) {
  return (
    <div className="min-h-screen bg-[#f4eddf] text-neutral-950">
      <SiteHeader />

      <main className="mx-auto max-w-[1180px] px-5 py-10 md:px-8 md:py-14">
        <section className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[#8a6a34]">
            {eyebrow}
          </div>
          <h1 className="mt-5 max-w-4xl text-[34px] font-semibold leading-[1.08] tracking-[-0.05em] text-neutral-950 sm:text-[42px] md:text-[56px]">
            {title}
          </h1>
          <p className="mt-6 max-w-3xl text-sm leading-7 text-neutral-700">
            {intro}
          </p>
        </section>

        <section className="mt-8 grid gap-5">
          {sections.map((section) => (
            <article
              key={section.title}
              className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-7 shadow-[0_12px_32px_rgba(75,55,25,0.06)]"
            >
              <h2 className="text-[24px] font-semibold tracking-[-0.035em] text-neutral-950">
                {section.title}
              </h2>
              <div className="mt-4 space-y-4 text-sm leading-7 text-neutral-700">
                {section.body.map((paragraph) => (
                  <p key={paragraph}>{paragraph}</p>
                ))}
              </div>
            </article>
          ))}
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
