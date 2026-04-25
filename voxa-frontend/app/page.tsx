import Link from "next/link";

import DesktopDisclosure from "./desktop-disclosure";
import SiteHeader from "./site-header";
import SiteFooter from "./site-footer";
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
    <>
    <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
      <SiteHeader activeItem="product" />

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
          <DesktopDisclosure
            id="product"
            eyebrow="Why VoxaRisk exists"
            title="Structured contract risk intelligence for commercial review."
            intro="VoxaRisk is designed for executive and commercial users who need a fast exposure view before a contract moves deeper into internal approval or external negotiation."
            defaultDesktopOpen
            className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
          >
            <div className="grid gap-5 md:grid-cols-3">
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
          </DesktopDisclosure>

          <DesktopDisclosure
            id="fit"
            eyebrow="Decision discipline"
            title="For commercial teams that need clarity before escalation."
            intro="Use the platform to improve review discipline, strengthen approval consistency, and focus escalation only where the consequence warrants it."
            className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
          >
            <div className="space-y-3">
              {bestFitGroups.map((item) => (
                <div key={item} className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] px-4 py-4 text-sm leading-6 text-neutral-700">
                  {item}
                </div>
              ))}
            </div>
          </DesktopDisclosure>
        </div>

        <DesktopDisclosure
          eyebrow="AI-assisted, evidence-governed"
          title="AI, governed by evidence rather than guesswork."
          intro="VoxaRisk uses deterministic risk detection first, then applies AI as a controlled explanation layer for eligible plans. The underlying score, severity, findings, and evidence remain engine-governed."
          className="mt-8 rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
        >
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
            {[
              "Deterministic findings first",
              "AI explanation second",
              "Evidence-backed review notes",
              "No legal-advice substitution",
              "No AI override of score or severity",
            ].map((item) => (
              <div
                key={item}
                className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] px-4 py-4 text-sm font-medium leading-6 text-neutral-800"
              >
                {item}
              </div>
            ))}
          </div>
        </DesktopDisclosure>

        <div id="workflow" className="mt-8 grid gap-8 lg:grid-cols-[0.95fr_1.05fr]">
          <DesktopDisclosure
            id="workflow"
            eyebrow="How the intelligence works"
            title="Detection to user decision, without pretending to decide for you."
            intro="The product turns clause-level signals into a disciplined commercial review sequence so teams can move from scan to decision with a clearer evidence trail."
            className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
          >
            <div className="grid gap-4">
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
          </DesktopDisclosure>

          <DesktopDisclosure
            eyebrow="What the report shows"
            title="Use the platform to focus review, not to outsource accountability."
            intro="Treat the output as a disciplined review layer: start with the decision signal, inspect the evidence, then escalate only where the commercial consequence warrants it."
            className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
          >
            <div className="grid gap-3 md:grid-cols-2">
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
                Escalate when the scan surfaces uncapped liability, broad indemnity, unilateral price movement, suspension rights, unusual jurisdiction, weak termination protection, or repeated high-priority findings across the same contract.
              </p>
            </div>

            <div className="mt-4 rounded-[1rem] border border-[#d2bd96] bg-[#fbf3e5] p-5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                Product boundaries
              </div>
              <p className="mt-3 text-sm leading-6 text-neutral-700">
                VoxaRisk supports disciplined review and evidence-led escalation. It does not replace commercial judgment, legal advice, or approval accountability.
              </p>
            </div>
          </DesktopDisclosure>
        </div>
      </section>
    </main>
      <SiteFooter />
    </>
  );
}
