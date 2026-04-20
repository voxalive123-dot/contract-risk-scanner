import Link from "next/link";

const trustPillars = [
  {
    title: "Automated contract risk intelligence",
    body: "Surface structural exposure, clause-level leverage, and evidence-backed risk signals before commercial momentum narrows the room to respond.",
  },
  {
    title: "Prioritised review focus",
    body: "Turn dense drafting into a disciplined review order so founders, operators, commercial leaders, and in-house teams know what deserves attention first.",
  },
  {
    title: "Report-ready output",
    body: "Convert detected issues into a serious decision signal, negotiation priorities, clause evidence, and a printable contract risk report.",
  },
];

const workflowSteps = [
  {
    title: "Detection",
    body: "Scan pasted text or supported document input for clause patterns that can shift cost, control, leverage, or downside exposure.",
  },
  {
    title: "Analysis",
    body: "Translate those signals into structured observations, ranked priorities, confidence cues, and clause-linked evidence.",
  },
  {
    title: "Insights",
    body: "Present an executive summary, decision posture, negotiation focus, and report-ready output for structured internal review.",
  },
  {
    title: "User Decision",
    body: "Keep final legal and commercial decisions with the user, their team, and professional advisers where appropriate.",
  },
];

const bestFitGroups = [
  "Founders and operators reviewing exposure before signature pressure builds",
  "Commercial leaders prioritising negotiation focus and approval discipline",
  "In-house teams triaging contract issues before deeper legal review",
  "Business users who need structured review support without a raw rule dump",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-neutral-100 text-neutral-950">
      <section className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-8 md:px-8 lg:py-12">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm lg:p-12">
          <div className="grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
            <div className="max-w-4xl">
              <div className="text-xs font-medium uppercase tracking-[0.28em] text-neutral-500">
                VoxaRisk Intelligence
              </div>

              <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight text-neutral-950 md:text-5xl">
                Executive-grade contract risk intelligence for disciplined commercial review.
              </h1>

              <p className="mt-5 max-w-3xl text-base leading-7 text-neutral-600">
                VoxaRisk provides automated contract risk intelligence and
                decision-support observations for teams reviewing contract
                exposure, negotiation posture, and report-ready output before
                final approval decisions are made.
              </p>

              <div className="mt-8 flex flex-wrap items-center gap-4">
                <Link
                  href="/dashboard"
                  className="rounded-2xl bg-black px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
                >
                  Open Executive Review
                </Link>

                <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-600">
                  Structured review support. Report-ready output. Users remain
                  responsible for decisions.
                </div>
              </div>
            </div>

            <div className="rounded-[1.75rem] border border-neutral-200 bg-neutral-50 p-6">
              <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                Decision boundary
              </div>
              <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
                Built to strengthen review discipline, not replace judgment.
              </h2>
              <p className="mt-4 text-sm leading-7 text-neutral-700">
                VoxaRisk helps teams spot risk signals, focus negotiation,
                inspect clause evidence, and generate a report. It does not
                provide legal advice, legal opinion, contract approval, or a
                guarantee of compliance.
              </p>
              <p className="mt-4 text-sm leading-7 text-neutral-700">
                Professional review remains appropriate where legal or
                high-consequence decisions are involved.
              </p>
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              What VoxaRisk does
            </div>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              Calm authority for first-pass contract review.
            </h2>

            <p className="mt-4 max-w-3xl text-sm leading-7 text-neutral-600">
              VoxaRisk is designed for executive and commercial users who need a
              fast exposure view before a contract moves deeper into internal
              approval or external negotiation. The product stays focused on
              structured review support rather than legal conclusions.
            </p>

            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {trustPillars.map((pillar) => (
                <div
                  key={pillar.title}
                  className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5"
                >
                  <h3 className="text-base font-semibold text-neutral-950">
                    {pillar.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-neutral-600">
                    {pillar.body}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              Best fit
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              For commercial teams that need clarity before escalation.
            </h2>

            <div className="mt-6 space-y-3">
              {bestFitGroups.map((item) => (
                <div
                  key={item}
                  className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-sm leading-6 text-neutral-700"
                >
                  {item}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              Review workflow
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              Detection to user decision, without pretending to decide for you.
            </h2>

            <div className="mt-8 space-y-4">
              {workflowSteps.map((step, index) => (
                <div
                  key={step.title}
                  className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5"
                >
                  <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                    Step {index + 1}
                  </div>
                  <h3 className="mt-2 text-base font-semibold text-neutral-950">
                    {step.title}
                  </h3>
                  <p className="mt-3 text-sm leading-6 text-neutral-600">
                    {step.body}
                  </p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              How to use the result
            </div>
            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              Use the platform to focus review, not to outsource accountability.
            </h2>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Start with signal
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Read the Decision Signal first, then move immediately into the
                  highest-ranked negotiation priorities and clause evidence.
                </p>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Use report output
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Generate a printable contract risk report when the review needs
                  to travel to executives, commercial stakeholders, or counsel.
                </p>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Keep evidence visible
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Check matched clause text and rationale before relying on a
                  result, especially when source quality or OCR confidence is weak.
                </p>
              </div>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
                <div className="text-xs uppercase tracking-[0.2em] text-neutral-500">
                  Preserve responsibility
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Users remain responsible for commercial and legal decisions and
                  should obtain professional advice where appropriate.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
