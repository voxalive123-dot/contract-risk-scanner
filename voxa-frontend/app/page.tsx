import Link from "next/link";

import DesktopDisclosure from "./desktop-disclosure";
import SiteHeader from "./site-header";
import SiteFooter from "./site-footer";

const trustPillars = [
  {
    title: "Cross-clause exposure analysis",
    body: "Identify clause combinations where ordinary-looking terms create stronger hidden exposure when read together.",
  },
  {
    title: "Policy-aware review posture",
    body: "Compare findings against organisation tolerance so teams can see what exceeds policy, conflicts with policy, or needs a documented exception.",
  },
  {
    title: "Audit-ready decision record",
    body: "Preserve review evidence, decision notes, escalation outcomes, and recurring risk families for future commercial governance.",
  },
];

const bestFitGroups = [
  "Founders and directors reviewing exposure before signature pressure builds",
  "Procurement and commercial teams comparing risk against internal tolerance",
  "Operators and consultants who need repeatable contract risk governance",
  "In-house teams triaging escalation points before deeper professional review",
];

const workflowSteps = [
  {
    title: "Detect",
    body: "Surface clause-level risk signals and linked evidence across liability, indemnity, data use, termination, payment, suspension, jurisdiction, and related risk families.",
  },
  {
    title: "Interpret",
    body: "Apply cross-clause intelligence, commercial context, and organisation policy so risk is framed as decision-ready exposure rather than a raw clause list.",
  },
  {
    title: "Record",
    body: "Capture whether issues were accepted, negotiated, escalated, rejected, or sent for legal review so future teams do not start from zero.",
  },
];

const crossClauseExamples = [
  "Low liability cap + broad indemnity",
  "Termination for convenience + no refund",
  "Broad data use + weak confidentiality",
  "Upfront payment + suspension rights",
];

const intelligenceSections = [
  {
    eyebrow: "Cross-clause intelligence",
    title: "Cross-clause intelligence for hidden commercial exposure",
    body: "VoxaRisk does not only detect isolated clauses. It identifies combinations where ordinary-looking terms create stronger exposure together, helping teams spot hidden cap, refund, data, and continuity risk before approval.",
  },
  {
    eyebrow: "Organisation memory",
    title: "From one-off review to organisational memory",
    body: "Each review can become part of the organisation's risk memory, helping teams retrieve previous reviews, see recurring risk families, and avoid starting from zero on every contract.",
  },
  {
    eyebrow: "Tolerance and policy",
    title: "See not only what is risky - see whether it exceeds your policy",
    body: "VoxaRisk can compare findings against organisation policy and tolerance settings, then show whether a finding exceeds tolerance, conflicts with policy, sits within configured tolerance, or remains policy-unknown.",
  },
  {
    eyebrow: "Decision memory",
    title: "Capture the decision, not just the detection",
    body: "Teams can record whether risks were accepted, negotiated, escalated, rejected, waived, redlined, or sent for legal review, creating an audit-ready history of commercial judgement.",
  },
  {
    eyebrow: "Executive governance",
    title: "Built for commercial governance, not casual document checking",
    body: "VoxaRisk is designed for founders, directors, procurement teams, operators, consultants, and commercial reviewers who need structured risk intelligence before signing.",
  },
  {
    eyebrow: "Review boundary",
    title: "Decision support, not legal advice",
    body: "VoxaRisk helps teams focus review, document decisions, identify escalation points, and support professional or legal review where needed. It does not provide legal advice, legal opinion, contract approval, or compliance certification.",
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
            <Eyebrow>Contract risk governance</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              Contract Risk Decision Intelligence for Commercial Leaders
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              VoxaRisk helps organisations detect hidden contract exposure, compare risks against internal tolerance, preserve decision history, and turn contract review into a repeatable governance process.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              {["Cross-clause intelligence", "Organisation memory", "Policy-aware review", "Audit-ready records"].map((item) => (
                <span key={item} className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-xs font-semibold text-neutral-950">
                  {item}
                </span>
              ))}
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-6 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
                Analyse a contract
              </Link>
              <Link href="/dashboard" className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]">
                View decision dashboard
              </Link>
              <Link href="/pricing" className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]">
                Start contract risk review
              </Link>
            </div>
          </div>

          <aside className="flex h-full flex-col justify-between rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
            <div>
              <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                Decision boundary
              </div>
              <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
                Executive contract risk intelligence without pretending to decide for you.
              </h2>
              <p className="mt-5 text-sm leading-7 text-neutral-700">
                Use VoxaRisk to strengthen review posture, preserve evidence, compare against tolerance, and document the commercial decision path before approval pressure builds.
              </p>
            </div>
            <p className="mt-8 rounded-2xl border border-[#dccaad] bg-[#fffdf8] p-5 text-sm leading-7 text-neutral-700">
              VoxaRisk provides commercial risk decision support. It does not provide legal advice, legal opinion, contract approval, compliance certification or universal jurisdiction outcomes. Users remain responsible for commercial and legal decisions and should obtain professional advice where appropriate.
            </p>
          </aside>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-6 pb-14 md:px-8">
        <div className="space-y-8">
          <DesktopDisclosure
            id="product"
            eyebrow="Decision intelligence engine"
            title="Structured contract risk intelligence for commercial governance."
            intro="VoxaRisk turns contract review into a governed decision process: detect risk, interpret clause interactions, compare against tolerance, preserve history, and record what happened next."
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
            eyebrow="Commercial governance"
            title="For teams that need decision-ready review before escalation."
            intro="Use the platform to improve approval consistency, identify escalation points, and keep a defensible record of contract risk decisions."
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
          eyebrow="Clause interaction"
          title="Cross-clause intelligence for hidden commercial exposure"
          intro="Important exposure often sits between clauses rather than inside one clause. VoxaRisk identifies combinations where the practical risk is stronger than each term looks in isolation."
          className="mt-8 rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {crossClauseExamples.map((item) => (
              <div
                key={item}
                className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] px-4 py-4 text-center text-[13px] font-medium leading-6 text-neutral-800"
              >
                {item}
              </div>
            ))}
          </div>
        </DesktopDisclosure>

        <DesktopDisclosure
          id="workflow"
          eyebrow="From detection to decision record"
          title="From contract signal to governed decision path"
          intro="The product turns clause-level evidence, context, tolerance, and prior outcomes into a structured review sequence commercial teams can act on and audit later."
          className="mt-8 rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]"
        >
          <div className="grid gap-8 lg:grid-cols-2 lg:items-stretch">
            <section className="flex h-full flex-col rounded-[1.15rem] border border-[#e0d1b7] bg-[#fcf6ec] p-6">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                How the intelligence works
              </div>
              <div className="mt-5 grid flex-1 gap-4 content-start">
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

            <section className="flex h-full flex-col rounded-[1.15rem] border border-[#e0d1b7] bg-[#fcf6ec] p-6">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                What the review record supports
              </div>
              <div className="mt-5 flex flex-1 flex-col gap-4">
                <div className="rounded-[1rem] border border-[#e0d1b7] bg-[#fffdf8] p-5">
                  <p className="text-sm leading-7 text-neutral-700">
                    Use the output to read the decision posture, inspect evidence, compare tolerance, document open issues, and escalate material exposure.
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  {[
                    "Inspect clause evidence",
                    "Compare against tolerance",
                    "Prioritise redlines",
                    "Record the outcome",
                  ].map((item) => (
                    <div
                      key={item}
                      className="rounded-[1rem] border border-[#e0d1b7] bg-[#fbf3e5] p-4 text-sm font-medium leading-6 text-neutral-800"
                    >
                      {item}
                    </div>
                  ))}
                </div>

                <div className="mt-auto grid gap-4 xl:grid-cols-2">
                  <div className="rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-5">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                      Escalation triggers
                    </div>
                    <p className="mt-3 text-sm leading-6 text-neutral-700">
                      Escalate when exposure exceeds tolerance, conflicts with policy, creates operational dependency, leaves unresolved evidence, or follows a risk family your organisation has previously escalated.
                    </p>
                  </div>

                  <div className="rounded-[1rem] border border-[#d2bd96] bg-[#fbf3e5] p-5">
                    <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                      Governance boundary
                    </div>
                    <p className="mt-3 text-sm leading-6 text-neutral-700">
                      VoxaRisk supports commercial review, escalation discipline, and decision records. It does not replace legal advice, commercial judgement, or approval accountability.
                    </p>
                  </div>
                </div>
              </div>
            </section>
          </div>
        </DesktopDisclosure>

        <section className="mt-8 grid gap-4 lg:grid-cols-2">
          {intelligenceSections.map((section) => (
            <article key={section.title} className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-6 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                {section.eyebrow}
              </div>
              <h2 className="mt-4 text-2xl font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
                {section.title}
              </h2>
              <p className="mt-4 text-sm leading-7 text-neutral-700">
                {section.body}
              </p>
            </article>
          ))}
        </section>
      </section>
    </main>
      <SiteFooter />
    </>
  );
}
