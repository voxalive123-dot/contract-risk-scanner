import Link from "next/link";

import SiteFooter from "../site-footer";
type Plan = {
  name: string;
  price: string;
  annual: string;
  description: string;
  cta: string;
  href: string;
  featured?: boolean;
  features: string[];
  checkoutOptions?: { label: string; href: string }[];
};

const plans: Plan[] = [
  {
    name: "Free",
    price: "£0",
    annual: "For first-pass testing and basic exposure signal.",
    description: "For validating whether a contract surfaces useful automated risk signals before deeper review.",
    cta: "Start Free",
    href: "/dashboard",
    features: ["Limited scans", "Summary score", "Basic decision signal", "Limited findings preview", "Upgrade for reports/export"],
  },
  {
    name: "Business",
    price: "£149/month",
    annual: "£1,490/year",
    description: "For teams running structured commercial review across recurring contract work.",
    cta: "Choose Business",
    href: "/dashboard",
    featured: true,
    features: ["Full findings", "Executive summary", "Negotiation priorities", "Clause evidence", "Report/export", "Higher scan/report limits", "Recurring commercial review", "Prioritised review focus", "Team-oriented positioning"],
    checkoutOptions: [
      { label: "Start Business monthly", href: "https://buy.stripe.com/eVq6oK3zJbJf36c9B83AY00" },
      { label: "Start Business annual", href: "https://buy.stripe.com/dRm5kGc6f3cJbCI3cK3AY01" },
    ],
  },
  {
    name: "Executive",
    price: "£499/month",
    annual: "£4,990/year",
    description: "For leadership teams needing stronger reporting discipline and review cadence.",
    cta: "Choose Executive",
    href: "/dashboard",
    features: ["Everything in Business", "Higher usage limits", "Executive reporting focus", "Leadership review cadence", "Stronger decision support"],
    checkoutOptions: [
      { label: "Start Executive monthly", href: "https://buy.stripe.com/14A9AW7PZ6oVdKQfZw3AY02" },
      { label: "Start Executive annual", href: "https://buy.stripe.com/6oU9AWdaj7sZ8qw3cK3AY03" },
    ],
  },
  {
    name: "Enterprise",
    price: "£299/month",
    annual: "£2,990/year",
    description: "For heavier review workflows, tailored limits, onboarding, or invoice-based access.",
    cta: "Contact Enterprise",
    href: "mailto:enterprise@voxarisk.com?subject=VoxaRisk%20Enterprise",
    features: ["Custom usage limits", "Governed deployment discussion", "Procurement/security review", "Commercial onboarding", "Enterprise terms"],
    checkoutOptions: [
      { label: "Start Enterprise monthly", href: "https://buy.stripe.com/fZu14q5HRaFb22828G3AY04" },
      { label: "Start Enterprise annual", href: "https://buy.stripe.com/dRm4gCc6f9B7eOUbJg3AY05" },
    ],
  },
];

const upgradeReasons = [
  { title: "Full reports", body: "Move beyond summary signal into clause evidence and executive-ready output." },
  { title: "Review discipline", body: "Prioritise what to redline before approval momentum builds." },
  { title: "Commercial repeatability", body: "Use the same structured method across recurring contract review." },
];

function SiteHeader() {
  return (
    <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-5 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <Link href="/" className="flex items-center justify-center gap-4 md:justify-start">
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
            <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b5d2c]">
              CONTRACT RISK INTELLIGENCE
            </div>
          </div>
        </Link>

        <nav className="flex items-center gap-3 text-sm text-neutral-700">
          <Link href="/" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">Product</Link>
          <Link href="/pricing" className="rounded-full border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b]">Pricing</Link>
          <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]">Dashboard</Link>
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

function PricingCard({ plan }: { plan: Plan }) {
  const featured = Boolean(plan.featured);
  const hasCheckoutOptions = Boolean(plan.checkoutOptions?.length);

  return (
    <article className={`relative flex h-full min-h-[520px] flex-col overflow-hidden rounded-[1.25rem] border bg-[#fffdf8] p-5 shadow-[0_14px_30px_rgba(75,55,25,0.07)] ${featured ? "border-[#8a6a34] ring-1 ring-[#b08d57]/40" : "border-[#dfcfb0]"}`}>
      <div className="absolute inset-x-0 top-0 h-[3px] bg-[#c2a46d]" />
      <div className="flex min-h-[28px] items-center justify-between gap-3 pt-1">
        <div className="text-[10px] font-semibold uppercase tracking-[0.3em] text-neutral-500">{plan.name}</div>
        {featured ? (
          <div className="rounded-full border border-[#c2a46d] bg-[#fff4dc] px-2.5 py-1 text-[9px] font-semibold uppercase tracking-[0.18em] text-[#765a2b]">Recommended</div>
        ) : (
          <span aria-hidden="true" className="h-[22px] w-[96px] shrink-0" />
        )}
      </div>

      <div className="mt-6 min-h-[72px]">
        <div className="text-[2rem] font-semibold tracking-[-0.045em] text-neutral-950">{plan.price}</div>
        <div className="mt-2 min-h-[1.25rem] text-sm text-neutral-500">{plan.annual}</div>
      </div>

      <p className="mt-5 min-h-[96px] text-[15px] leading-6 text-neutral-700">{plan.description}</p>

      <div className="mt-6 flex flex-1 flex-col">
        <div className="flex-1 border-t border-[#eadfcd]">
          {plan.features.map((feature) => (
            <div key={`${plan.name}-${feature}`} className="flex min-h-[42px] items-start gap-3 border-b border-[#eadfcd] py-2.5 text-sm leading-6 text-neutral-700">
              <span className="mt-[0.45rem] h-1.5 w-1.5 shrink-0 rounded-full bg-[#b08d57]" />
              <span>{feature}</span>
            </div>
          ))}
        </div>

        <div className="mt-auto pt-5">
          {hasCheckoutOptions ? (
            <div className="space-y-2.5">
              <p className="px-1 text-[12px] leading-5 text-neutral-500">
                Access activation may be completed after subscription confirmation.
              </p>
              {plan.checkoutOptions?.map((option, index) => (
                <a
                  key={`${plan.name}-${option.label}`}
                  href={option.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={`block rounded-xl px-4 py-3 text-center text-sm font-semibold transition ${
                    featured && index === 0
                      ? "bg-[#11110f] text-stone-100 hover:bg-[#1b1a17]"
                      : "border border-[#c6aa72] bg-white text-neutral-950 hover:bg-[#fff4dc]"
                  }`}
                >
                  {option.label}
                </a>
              ))}
            </div>
          ) : (
            <Link href={plan.href} className={`block rounded-xl px-4 py-3 text-center text-sm font-semibold transition ${featured ? "bg-[#11110f] text-stone-100 hover:bg-[#1b1a17]" : "border border-[#c6aa72] bg-white text-neutral-950 hover:bg-[#fff4dc]"}`}>
              {plan.cta}
            </Link>
          )}
        </div>
      </div>
    </article>
  );
}

export default function PricingPage() {
  return (
    <>
    <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
      <SiteHeader />

      <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
        <div className="grid gap-8 rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-stretch">
          <div className="flex flex-col justify-center">
            <Eyebrow>Public pricing</Eyebrow>
            <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
              Pricing for disciplined contract risk intelligence.
            </h1>
            <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
              Start with limited exposure signals, then upgrade for full reports, negotiation priorities, and executive-grade review output.
            </p>

            <div className="mt-7 flex flex-wrap gap-3">
              {["Evidence-backed findings", "Negotiation priority stack", "Report-ready executive output"].map((item) => (
                <span key={item} className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-xs font-semibold text-neutral-950">
                  {item}
                </span>
              ))}
            </div>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-6 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">Open Dashboard</Link>
              <Link href="/" className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]">Back to Home</Link>
            </div>
          </div>

          <aside className="flex h-full flex-col justify-center rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">Why teams upgrade</div>
            <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
              Turn early signal into disciplined commercial action.
            </h2>
            <p className="mt-5 text-sm leading-7 text-neutral-700">
              Paid tiers support full findings, clause evidence, negotiation focus, and report-ready output that can travel to decision-makers.
            </p>
          </aside>
        </div>
      </section>

      <section className="mx-auto max-w-[1360px] px-6 pb-14 md:px-8">
        <div className="grid gap-4 rounded-[1.5rem] border border-[#dccaad] bg-[#fbf2df] p-5 shadow-[0_16px_40px_rgba(75,55,25,0.07)] lg:grid-cols-3">
          {upgradeReasons.map((item) => (
            <article key={item.title} className="rounded-[1rem] border border-[#dccaad] bg-[#fffdf8] p-5">
              <div className="text-[11px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">{item.title}</div>
              <p className="mt-3 text-sm leading-6 text-neutral-700">{item.body}</p>
            </article>
          ))}
        </div>

        <section className="mt-8">
          <div className="rounded-[1.5rem] border border-[#d7c39b] bg-[#f8edd8] p-4 shadow-[0_20px_46px_rgba(75,55,25,0.10)]">
            <div className="mb-5 px-2">
              <Eyebrow>Pricing</Eyebrow>
              <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-neutral-950">
                Choose the review cadence that matches your risk exposure.
              </h2>
            </div>
            <div className="grid gap-4 xl:grid-cols-4">
              {plans.map((plan) => (
                <PricingCard key={plan.name} plan={plan} />
              ))}
            </div>
          </div>
        </section>

        <section className="mt-6 rounded-[1.25rem] border border-[#dccaad] bg-[#fffaf0] px-6 py-5 shadow-[0_10px_24px_rgba(75,55,25,0.05)]">
          <div className="max-w-[1180px] text-sm leading-7 text-neutral-700">
            <span className="font-semibold text-neutral-950">Plan logic:</span>{" "}
            Free validates signal. Business is the default commercial plan. Executive and Enterprise support higher-volume leadership and governed deployment.
          </div>
        </section>

        <section className="mt-6 rounded-[1.25rem] border border-[#d8c49e] bg-[#fffaf0] px-6 py-5 shadow-[0_10px_24px_rgba(75,55,25,0.05)]">
          <div className="max-w-[980px]">
            <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8a6a34]">Decision boundary</div>
            <p className="mt-4 text-sm leading-7 text-neutral-700">
              VoxaRisk provides automated contract risk intelligence and decision-support observations. It does not provide legal advice, legal opinion, contract approval, or a guarantee of compliance. Users remain responsible for commercial and legal decisions and should obtain professional advice where appropriate.
            </p>
          </div>
        </section>
      </section>
    </main>
      <SiteFooter />
    </>
  );
}
