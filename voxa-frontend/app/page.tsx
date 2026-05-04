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
        <div className="relative overflow-hidden border border-[#dfd0b6] bg-[#fffaf0] shadow-[0_24px_70px_rgba(75,55,25,0.10)]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(176,141,87,0.14),transparent_30%),linear-gradient(135deg,#fffaf0_0%,#f7ecd8_100%)]" />
          <div className="absolute inset-0 opacity-30 [background-image:linear-gradient(rgba(176,141,87,0.14)_1px,transparent_1px),linear-gradient(90deg,rgba(176,141,87,0.10)_1px,transparent_1px)] [background-size:38px_38px]" />
          <div className="relative grid gap-10 p-7 md:p-10 lg:grid-cols-[0.8fr_1.2fr] lg:items-center lg:p-12">
            <div className="flex min-h-[430px] flex-col justify-center">
              <Eyebrow>Contract risk governance</Eyebrow>
              <h1 className="mt-6 max-w-3xl text-4xl font-semibold leading-[1.04] text-neutral-950 md:text-5xl">
                Contract Risk Intelligence That Surfaces What Others Miss
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-neutral-700">
                Rules-first review, evidence trails, and decision outputs for teams that need commercial risk clarity before signature pressure builds.
              </p>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link href="/dashboard" className="bg-[#11110f] px-6 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
                  Run a contract scan
                </Link>
                <Link href="#product" className="border border-[#b08d57] bg-transparent px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#fff6e4]">
                  See how it works
                </Link>
              </div>
            </div>

            <aside className="relative w-full overflow-hidden bg-[#0c0c0c] p-4 text-stone-100 shadow-[0_30px_80px_rgba(17,17,15,0.24)] ring-1 ring-[#b08d57]/35 md:p-5 lg:my-6">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_72%_16%,rgba(176,141,87,0.20),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.05)_0%,transparent_38%)]" />
              <div className="absolute inset-0 opacity-[0.18] [background-image:linear-gradient(rgba(213,189,136,0.42)_1px,transparent_1px),linear-gradient(90deg,rgba(213,189,136,0.32)_1px,transparent_1px)] [background-size:32px_32px]" />
              <div className="relative border border-[#b08d57]/45 bg-[#11110f]/86 p-4 shadow-[0_0_45px_rgba(176,141,87,0.12)] md:p-5">
                <div className="flex flex-col gap-3 border-b border-[#b08d57]/45 pb-4 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#d5bd88]">Decision intelligence command interface</div>
                    <div className="mt-2 text-sm text-stone-300">Rules, evidence, exposure score, and action posture in one governed view.</div>
                  </div>
                  <div className="h-px bg-[#b08d57]/70 sm:h-10 sm:w-px" />
                  <div className="font-mono text-[11px] uppercase tracking-[0.18em] text-stone-400">Live review mode</div>
                </div>

                <div className="mt-5 grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
                  <section className="border border-[#b08d57]/35 bg-[#0c0c0c]/84 p-4">
                    <div className="flex items-center justify-between gap-4 border-b border-[#b08d57]/35 pb-3">
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">Contract Intake</h2>
                      <span className="font-mono text-[11px] text-stone-500">SOURCE TEXT</span>
                    </div>
                    <blockquote className="mt-4 font-mono text-sm leading-7 text-stone-200">
                      &quot;Supplier shall indemnify and keep indemnified the Customer against any and all loss, damage, liability, legal fees and costs...&quot;
                    </blockquote>
                    <div className="mt-5 h-px bg-[linear-gradient(90deg,rgba(176,141,87,0.85),transparent)]" />
                    <div className="mt-4 grid gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-stone-500 sm:grid-cols-3">
                      <span>Rule match</span>
                      <span>Evidence bound</span>
                      <span>Clause context</span>
                    </div>
                  </section>

                  <section className="border border-[#b08d57]/35 bg-[#0c0c0c]/84 p-4">
                    <div className="border-b border-[#b08d57]/35 pb-3">
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">Detected Signals</h2>
                    </div>
                    <div className="mt-4 space-y-3 font-mono text-sm text-stone-200">
                      {["Broad indemnity", "Cross-contract set-off", "Termination leverage"].map((signal) => (
                        <div key={signal} className="flex items-center gap-3">
                          <span className="h-px w-5 bg-[#b08d57]" />
                          <span>{signal}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-[0.85fr_1.15fr]">
                  <section className="border border-[#b08d57]/35 bg-[#0c0c0c]/84 p-4">
                    <div className="border-b border-[#b08d57]/35 pb-3">
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">Risk Score</h2>
                    </div>
                    <div className="mt-5 flex items-end justify-between gap-4">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-[0.22em] text-stone-400">High exposure</div>
                        <div className="mt-2 text-5xl font-semibold leading-none text-stone-100">28</div>
                      </div>
                      <div className="h-20 w-px bg-[#b08d57]/60" />
                      <div className="max-w-[150px] text-xs leading-5 text-stone-400">Financial exposure, control imbalance, and termination pressure elevated.</div>
                    </div>
                  </section>

                  <section className="border border-[#d5bd88]/60 bg-[#15130f] p-4 shadow-[0_0_34px_rgba(176,141,87,0.13)]">
                    <div className="border-b border-[#b08d57]/45 pb-3">
                      <h2 className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#d5bd88]">Decision Output</h2>
                    </div>
                    <div className="mt-5 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
                      <div>
                        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-stone-500">Recommended posture</div>
                        <div className="mt-2 text-2xl font-semibold uppercase text-stone-100 md:text-3xl">Hold / Renegotiate</div>
                      </div>
                      <div className="h-px bg-[#b08d57]/55 sm:h-12 sm:w-px" />
                      <div className="text-sm leading-6 text-stone-300">Escalate broad indemnity, set-off, and termination leverage before approval.</div>
                    </div>
                  </section>
                </div>
              </div>
            </aside>
          </div>
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
