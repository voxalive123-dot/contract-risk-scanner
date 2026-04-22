import Link from "next/link";
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

function SiteHeader() {
  return (
    <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] items-center justify-between px-6 py-5 md:px-8">
        <Link href="/" className="flex items-center gap-4">
          <div className="flex h-[76px] w-[76px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
            <img
              src="/brand/voxa-circle-logo.png"
              alt="VOXA"
              className="h-full w-full rounded-full object-cover object-center"
            />
          </div>
          <div className="leading-none">
            <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">
              VOXARISK
            </div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-[0.32em] text-[#8a6a34]">
              Contract Risk Intelligence
            </div>
          </div>
        </Link>

        <nav className="flex items-center gap-4 text-sm font-medium text-neutral-700">
          <Link href="/" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">
            Product
          </Link>
          <Link href="/#workflow" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">
            Workflow
          </Link>
          <Link href="/pricing" className="rounded-full border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b]">
            Pricing
          </Link>
          <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
            Dashboard
          </Link>
        </nav>
      </div>
    </header>
  );
}

export default function LegalPage({ eyebrow, title, intro, sections }: LegalPageProps) {
  return (
    <div className="min-h-screen bg-[#f4eddf] text-neutral-950">
      <SiteHeader />

      <main className="mx-auto max-w-[1180px] px-6 py-14 md:px-8">
        <section className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[#8a6a34]">
            {eyebrow}
          </div>
          <h1 className="mt-5 max-w-4xl text-[42px] font-semibold leading-[1.05] tracking-[-0.05em] text-neutral-950 md:text-[56px]">
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
