import Image from "next/image";
import Link from "next/link";

const trustPillars = [
  {
    title: "Evidence-backed risk signals",
    body: "Surface structural exposure, clause-level leverage, and matched evidence before approval momentum narrows the room to respond.",
  },
  {
    title: "Prioritised review focus",
    body: "Turn dense contract wording into a disciplined review order so teams know what deserves attention first.",
  },
  {
    title: "Report-ready output",
    body: "Convert detected issues into decision posture, negotiation priorities, clause evidence, and printable executive output.",
  },
];

const bestFitGroups = [
  "Founders and operators reviewing exposure before signature pressure builds",
  "Commercial leaders prioritising negotiation focus and approval discipline",
  "In-house teams triaging contract issues before deeper legal review",
  "Business users needing structured review support without a raw rule dump",
];

const workflowSteps = [
  {
    title: "Detect",
    body: "Scan contract text for clause structures that can shift cost, control, leverage, or downside exposure.",
  },
  {
    title: "Prioritise",
    body: "Rank exposure into a practical review order with confidence cues and clause-linked evidence.",
  },
  {
    title: "Decide",
    body: "Use the output to focus negotiation, internal escalation, and professional review where appropriate.",
  },
];

function SiteHeader() {
  return (
    <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] items-center justify-between px-6 py-5 md:px-8">
        <Link href="/" className="flex items-center gap-4">
          <div className="flex h-[76px] w-[76px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
            <Image
              src="/brand/voxa-circle-logo.png"
              alt="VOXA"
              width={1024}
              height={1024}
              className="h-full w-full scale-[1.12] object-cover object-center"
              priority
            />
          </div>
          <div className="leading-none">
            <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">
              VOXARISK
            </div>
            <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b5d2c]">
              CONTRACT RISK INTELLIGENCE
            </div>
          </div>
        </Link>

        <nav className="flex items-center gap-3 text-sm text-neutral-700">
          <a href="#product" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">
            Product
          </a>
          <a href="#workflow" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">
            Workflow
          </a>
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

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

export default function HomePage() {
  return (
    <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
        <div className="grid gap-8 rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-stretch">
          <div className="flex min-h-[430px] flex-col justify-center">
            <Eyebrow>Public overview</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              Executive-grade contract risk intelligence for disciplined commercial review.
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              VoxaRisk provides automated contract risk intelligence and decision-support observations for teams reviewing contract exposure, negotiation posture, and report-ready output before final approval decisions are made.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              {["Evidence-backed risk signals", "Prioritised review focus", "Report-ready output"].map((item) => (
                <span key={item} className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-xs font-semibold text-neutral-950">
                  {item}
                </span>
              ))}
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-6 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
                Open Dashboard
              </Link>
              <Link href="/pricing" className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]">
                View Pricing
              </Link>
            </div>
          </div>

          <aside className="flex h-full flex-col justify-between rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                Decision boundary
              </div>
              <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
                Executive clarity without pretending to decide for you.
              </h2>
              <p className="mt-5 text-sm leading-7 text-neutral-700">
                Use VoxaRisk to strengthen review discipline, surface evidence, and focus negotiation before approval pressure builds.
              </p>
            </div>
            <p className="mt-8 rounded-2xl border border-[#dccaad] bg-[#fffdf8] p-5 text-sm leading-7 text-neutral-700">
              VoxaRisk provides automated contract risk intelligence and decision-support observations. It does not provide legal advice, legal opinion, contract approval, or a guarantee of compliance. Users remain responsible for commercial and legal decisions and should obtain professional advice where appropriate.
            </p>
          </aside>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-6 pb-14 md:px-8">
        <div className="grid gap-8 lg:grid-cols-[1.25fr_0.75fr]">
          <section id="product" className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>What VoxaRisk does</Eyebrow>
            <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
              Structured contract risk intelligence for commercial review.
            </h2>
            <p className="mt-5 max-w-5xl text-base leading-8 text-neutral-700">
              VoxaRisk is designed for executive and commercial users who need a fast exposure view before a contract moves deeper into internal approval or external negotiation. The product stays focused on structured review support rather than legal conclusions.
            </p>

            <div className="mt-8 grid gap-5 md:grid-cols-3">
              {trustPillars.map((pillar) => (
                <article key={pillar.title} className="flex h-full flex-col rounded-[1.2rem] border border-[#e0d1b7] bg-[#fbf3e5] p-5">
                  <h3 className="min-h-[48px] text-base font-semibold text-neutral-950">
                    {pillar.title}
                  </h3>
                  <p className="mt-3 flex-1 text-sm leading-6 text-neutral-700">
                    {pillar.body}
                  </p>
                </article>
              ))}
            </div>
          </section>

          <section id="fit" className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>Best fit</Eyebrow>
            <h2 className="mt-5 text-[28px] font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
              For commercial teams that need clarity before escalation.
            </h2>
            <div className="mt-7 space-y-3">
              {bestFitGroups.map((item) => (
                <div key={item} className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] px-4 py-4 text-sm leading-6 text-neutral-700">
                  {item}
                </div>
              ))}
            </div>
          </section>
        </div>

        <div id="workflow" className="mt-8 grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
          <section className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>Review workflow</Eyebrow>
            <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
              Detection to user decision, without pretending to decide for you.
            </h2>
            <div className="mt-7 grid gap-4">
              {workflowSteps.map((step, index) => (
                <article key={step.title} className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] p-5">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">
                    Step {index + 1}
                  </div>
                  <h3 className="mt-2 text-base font-semibold text-neutral-950">{step.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-neutral-700">{step.body}</p>
                </article>
              ))}
            </div>
          </section>

          <section className="flex h-full flex-col rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
            <Eyebrow>How to use the result</Eyebrow>
            <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
              Use the platform to focus review, not to outsource accountability.
            </h2>

            <p className="mt-4 text-sm leading-7 text-neutral-700">
              Treat the output as a disciplined review layer: start with the
              decision signal, inspect the evidence, then escalate only where
              the commercial consequence warrants it.
            </p>

            <div className="mt-6 grid gap-3 md:grid-cols-2">
              {[
                "Read the decision signal first",
                "Inspect clause evidence",
                "Prioritise redlines",
                "Escalate where consequence warrants",
              ].map((item) => (
                <div
                  key={item}
                  className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] p-4 text-sm font-medium leading-6 text-neutral-800"
                >
                  {item}
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                Escalation triggers
              </div>
              <p className="mt-3 text-sm leading-6 text-neutral-700">
                Escalate when the scan surfaces uncapped liability, broad
                indemnity, unilateral price movement, suspension rights,
                unusual jurisdiction, weak termination protection, or repeated
                high-priority findings across the same contract.
              </p>
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}
