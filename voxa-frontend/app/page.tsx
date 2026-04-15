import Link from "next/link";

const pillars = [
  {
    title: "Decision-first risk review",
    body: "Surface the clauses most likely to shift leverage, cost, control, or downside exposure before approval momentum takes over.",
  },
  {
    title: "Evidence-backed priority stack",
    body: "Show the highest-value review points first, with clause evidence, business consequence, and recommended action aligned to the detected risk.",
  },
  {
    title: "Executive-grade output",
    body: "Convert clause detection into a commercial decision signal that leaders can understand quickly without reading like a raw rule dump.",
  },
];

const signals = [
  "Flags structural exposure early",
  "Ranks negotiation priorities fast",
  "Separates signal, evidence, detail",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-neutral-100 text-neutral-950">
      <section className="mx-auto flex max-w-7xl flex-col gap-10 px-6 py-8 md:px-8 lg:py-12">
        <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm lg:p-12">
          <div className="max-w-4xl">
            <div className="text-xs font-medium uppercase tracking-[0.28em] text-neutral-500">
              VoxaRisk Intelligence
            </div>

            <h1 className="mt-4 max-w-4xl text-4xl font-semibold tracking-tight text-neutral-950 md:text-5xl">
              Contract exposure intelligence for disciplined commercial decisions.
            </h1>

            <p className="mt-5 max-w-3xl text-base leading-7 text-neutral-600">
              VoxaRisk surfaces structural exposure, negotiation pressure points, and review priorities before commercial momentum narrows judgment. It is built to support faster, evidence-backed contract decisions — not to replace legal review.
            </p>

            <div className="mt-8 flex flex-wrap items-center gap-4">
              <Link
                href="/dashboard"
                className="rounded-2xl bg-black px-6 py-3 text-sm font-medium text-white transition hover:opacity-90"
              >
                Open Executive Review
              </Link>

              <div className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-3 text-sm text-neutral-600">
                Automated contract risk intelligence. Not legal advice.
              </div>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {signals.map((signal) => (
                <div
                  key={signal}
                  className="rounded-2xl border border-neutral-200 bg-neutral-50 px-4 py-4 text-sm leading-6 text-neutral-700"
                >
                  {signal}
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.4fr_0.9fr]">
          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              Why it exists
            </div>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              Commercial exposure is often missed when review discipline breaks down.
            </h2>

            <p className="mt-4 max-w-3xl text-sm leading-7 text-neutral-600">
              Material contract exposure is often discovered after leverage has already weakened. VoxaRisk is
              designed to surface structural risk early enough to strengthen negotiation posture,
              approval discipline, and commercial judgment.
            </p>

            <div className="mt-8 grid gap-4 md:grid-cols-3">
              {pillars.map((pillar) => (
                <div
                  key={pillar.title}
                  className="rounded-2xl border border-neutral-200 bg-neutral-50 p-5"
                >
                  <h3 className="text-base font-semibold text-neutral-950">{pillar.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-neutral-600">{pillar.body}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[2rem] border border-neutral-200 bg-white p-8 shadow-sm">
            <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
              Review doctrine
            </div>

            <h2 className="mt-3 text-2xl font-semibold tracking-tight text-neutral-950">
              Built to strengthen judgment, not replace it.
            </h2>

            <div className="mt-5 space-y-4 text-sm leading-7 text-neutral-600">
              <p>
                VoxaRisk turns clause-level risk signals into a structured commercial review view.
                It shows where exposure sits, why it matters, and what deserves immediate
                attention first.
              </p>

              <p>
                Final legal, commercial, and approval decisions remain with the user and their
                advisers. VoxaRisk is intentionally positioned as contract risk intelligence, not
                legal advice, certification, or approval.
              </p>
            </div>

            <div className="mt-8 rounded-2xl border border-neutral-200 bg-neutral-50 p-5">
              <div className="text-xs font-medium uppercase tracking-[0.24em] text-neutral-500">
                Best fit
              </div>
              <div className="mt-3 text-sm leading-7 text-neutral-700">
                In-house teams, founders, operators, and commercial leaders who need a fast,
                structured exposure view before deeper legal review.
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
