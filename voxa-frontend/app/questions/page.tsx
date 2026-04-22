import Link from "next/link";

import SiteFooter from "../site-footer";

type QuestionCard = {
  question: string;
  answer: string;
};

type QuestionGroup = {
  title: string;
  eyebrow: string;
  items: QuestionCard[];
};

const questionGroups: QuestionGroup[] = [
  {
    eyebrow: "What VoxaRisk is for",
    title: "A disciplined first-pass risk intelligence layer.",
    items: [
      {
        question: "What is VoxaRisk?",
        answer:
          "VoxaRisk is a contract risk intelligence platform. It scans commercial contract text for risk-bearing patterns, prioritises findings, and presents evidence-backed signals so users can review agreements more deliberately before negotiation, approval, or internal escalation.",
      },
      {
        question: "What problem does VoxaRisk solve?",
        answer:
          "Most contract risk is missed because review is rushed, unstructured, or buried in dense wording. VoxaRisk gives users a disciplined first-pass review layer: what looks risky, where it appears, why it matters, and what deserves attention first.",
      },
      {
        question: "What does a scan produce?",
        answer:
          "Depending on the plan and input quality, a scan can produce a risk score, severity signal, flagged findings, clause evidence, executive summary, decision posture, negotiation priorities, and report/export output.",
      },
      {
        question: "What risks can VoxaRisk detect?",
        answer:
          "VoxaRisk is built to detect common commercial exposure patterns such as broad indemnity, unilateral termination rights, price increase rights, jurisdiction concerns, liability issues, service discretion, and other contract control signals. Coverage expands over time, but no automated tool can catch everything.",
      },
      {
        question: "Who is VoxaRisk best suited for?",
        answer:
          "Businesses, founders, consultants, managers, operators, and teams that regularly review commercial contracts and want a disciplined first-pass risk intelligence layer before deeper review.",
      },
      {
        question: "What makes VoxaRisk different?",
        answer:
          "VoxaRisk is not trying to sound clever; it is trying to be controlled. It combines rule-based detection, evidence-backed findings, severity, decision posture, report output, and clear product boundaries so contract review becomes more structured and less improvised.",
      },
    ],
  },
  {
    eyebrow: "Boundaries and responsibility",
    title: "Decision support without pretending to replace legal judgment.",
    items: [
      {
        question: "Is VoxaRisk a law firm or solicitor service?",
        answer:
          "No. VoxaRisk is software. It does not provide legal advice, legal opinions, solicitor services, contract approval, or a guarantee that an agreement is safe. It helps users identify and organise risk signals.",
      },
      {
        question: "Can I rely on VoxaRisk instead of legal advice?",
        answer:
          "No. VoxaRisk is decision support, not a substitute for legal advice. It helps users spot issues earlier and structure review priorities. Legally binding decisions remain with the user and professional advisers where needed.",
      },
      {
        question: "Does VoxaRisk guarantee it will find every risk?",
        answer:
          "No. No automated review tool can guarantee that. VoxaRisk gives structured risk signals based on detected patterns and available text. Users remain responsible for final judgment, escalation, negotiation, and professional review.",
      },
      {
        question: "What should I do with a high-risk result?",
        answer:
          "Do not ignore it. Review the clause evidence, identify negotiation priorities, consider commercial impact, and escalate to legal or senior review where appropriate. VoxaRisk organises the issue; it does not make the final decision.",
      },
    ],
  },
  {
    eyebrow: "Subscriptions and access",
    title: "Billing should be clear, deliberate, and mapped to the right account.",
    items: [
      {
        question: "What happens after I subscribe?",
        answer:
          "Payment is processed through Stripe. After subscription confirmation, access activation may be completed and the selected entitlement can be applied to the correct VoxaRisk account or organisation.",
      },
      {
        question: "Why does access activation say it may be completed after confirmation?",
        answer:
          "Because billing access must map cleanly to the correct user or organisation. VoxaRisk is deliberately avoiding unsafe automatic upgrades based only on email. That protects customers and prevents entitlement errors.",
      },
      {
        question: "What is the difference between Free, Business, Executive, and Enterprise?",
        answer:
          "Free validates signal. Business is the default commercial plan for recurring contract review. Executive supports leadership-focused and higher-volume review workflows. Enterprise is for heavier governed deployment, tailored limits, onboarding, procurement/security review, or invoice-based access.",
      },
      {
        question: "Can a firm or team use VoxaRisk?",
        answer:
          "Yes. Enterprise is intended for organisation-oriented use, including firms, consultants, commercial teams, and internal review groups. Access and deployment can be configured through controlled onboarding so the subscription maps properly to the right organisation, usage expectations, and billing context. VoxaRisk remains a contract risk intelligence tool, not a legal-advice or solicitor-service substitute.",
      },
      {
        question: "Does Enterprise include self-serve team management?",
        answer:
          "Full self-serve team administration should be introduced only when the account and permissions layer is ready. Current Enterprise access should be treated as controlled organisation onboarding rather than a promise of instant user invites, SSO, or unlimited seats.",
      },
      {
        question: "Can I cancel a subscription?",
        answer:
          "Subscriptions are handled through Stripe billing infrastructure. Account-management and customer-portal flows should be connected as the billing layer matures, so customers can manage billing details through the appropriate route.",
      },
    ],
  },
  {
    eyebrow: "Data, reliability, and scan quality",
    title: "Result quality depends on the text, the signal, and the review boundary.",
    items: [
      {
        question: "Does VoxaRisk read the whole contract?",
        answer:
          "VoxaRisk analyses the text it receives. If the pasted or uploaded material is incomplete, unclear, image-heavy, or poorly extracted, the result may be incomplete. Confidence and evidence signals help users judge the strength of the scan.",
      },
      {
        question: "Are contracts stored permanently?",
        answer:
          "VoxaRisk processes submitted contract material to provide analysis and may store scan metadata or outputs where required for service operation, reporting, audit, or account usage. Users should only submit material they are authorised to review or process. More detail is available in the Privacy Policy.",
      },
      {
        question: "Is my contract data used to train public AI models?",
        answer:
          "VoxaRisk is designed as a governed contract risk platform. Future AI features should be added as controlled augmentation, not uncontrolled public-model training. Current data-handling terms should be read in the Privacy Policy and product notices.",
      },
    ],
  },
  {
    eyebrow: "VoxaRisk and AI",
    title: "Controlled AI augmentation, not black-box judgment.",
    items: [
      {
        question: "Does VoxaRisk use AI?",
        answer:
          "Yes. VoxaRisk is being designed as an AI-enabled contract risk intelligence platform. The core scan remains governed by deterministic findings, severity signals, and clause evidence. AI is used as a controlled explanation layer, not as an uncontrolled legal chatbot.",
      },
      {
        question: "Does AI decide the risk score?",
        answer:
          "No. The risk score, severity, findings, and clause evidence come from VoxaRisk’s deterministic analysis layer. AI Review Notes may explain those results in clearer commercial language, but they do not change the score or override the findings.",
      },
      {
        question: "Why is that safer than a generic AI chatbot?",
        answer:
          "Generic AI can sound confident even when it is not grounded. VoxaRisk constrains AI to the detected findings and matched evidence, so the explanation stays closer to the actual scan result and does not become a free-form legal opinion.",
      },
      {
        question: "Can AI Review Notes replace a lawyer?",
        answer:
          "No. AI Review Notes are decision-support content. They can help users understand what to review, clarify, or escalate, but they are not legal advice, legal opinion, contract approval, or a guarantee that a contract is safe.",
      },
      {
        question: "Why does VoxaRisk combine rules and AI?",
        answer:
          "Rules provide structure, repeatability, and evidence discipline. AI adds readability, explanation, and commercial framing. The combination is designed to make contract review more understandable without surrendering control to a black-box answer.",
      },
    ],
  },
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
          <Link href="/" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">
            Product
          </Link>
          <Link
            href="/pricing"
            className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950"
          >
            Pricing
          </Link>
          <Link
            href="/questions"
            className="rounded-full border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b]"
          >
            Questions
          </Link>
          <Link
            href="/dashboard"
            className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
          >
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

function QuestionSection({ group }: { group: QuestionGroup }) {
  return (
    <section className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-8 shadow-[0_16px_40px_rgba(75,55,25,0.07)]">
      <Eyebrow>{group.eyebrow}</Eyebrow>
      <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
        {group.title}
      </h2>
      <div className="mt-7 grid gap-4">
        {group.items.map((item) => (
          <article
            key={item.question}
            className="rounded-[1.1rem] border border-[#e0d1b7] bg-[#fbf3e5] p-5"
          >
            <h3 className="text-base font-semibold text-neutral-950">{item.question}</h3>
            <p className="mt-3 text-sm leading-7 text-neutral-700">{item.answer}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function QuestionsPage() {
  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader />

        <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
          <div className="grid gap-8 rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10 lg:grid-cols-[1.08fr_0.92fr] lg:items-stretch">
            <div className="flex min-h-[430px] flex-col justify-center">
              <Eyebrow>VoxaRisk intelligence</Eyebrow>
              <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
                Understanding VoxaRisk Intelligence
              </h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
                VoxaRisk is built to support disciplined contract review. This page explains what the platform does, what it does not do, and how to use its output with the right commercial judgment.
              </p>

              <div className="mt-7 flex flex-wrap gap-3">
                {[
                  "Risk signals before escalation",
                  "Clear product boundaries",
                  "Subscription clarity before commitment",
                ].map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-xs font-semibold text-neutral-950"
                  >
                    {item}
                  </span>
                ))}
              </div>

              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/pricing"
                  className="rounded-xl bg-[#11110f] px-6 py-3 text-center text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
                >
                  Review Pricing
                </Link>
                <Link
                  href="/dashboard"
                  className="rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-6 py-3 text-center text-sm font-semibold text-neutral-950 transition hover:bg-[#f3e4c6]"
                >
                  Open Dashboard
                </Link>
              </div>
            </div>

            <aside className="flex h-full flex-col justify-between rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
              <div>
                <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                  Before you subscribe
                </div>
                <h2 className="mt-5 text-3xl font-semibold leading-tight tracking-[-0.04em] text-neutral-950">
                  Buy when the review boundary is clear.
                </h2>
                <p className="mt-5 text-sm leading-7 text-neutral-700">
                  The strongest customers are usually the ones who understand the product boundary before they rely on the output. That keeps expectations clean and deployment safer.
                </p>
              </div>

              <div className="mt-8 rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-5">
                <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">
                  Subscription checkpoint
                </div>
                <p className="mt-3 text-sm leading-6 text-neutral-700">
                  Review the plans, access activation note, and product boundary before you subscribe.
                </p>
                <Link
                  href="/pricing"
                  className="mt-4 inline-flex items-center rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-xs font-semibold tracking-[0.04em] text-neutral-950 transition hover:bg-[#f3e4c6]"
                >
                  Back to pricing
                </Link>
              </div>
            </aside>
          </div>
        </section>

        <section className="mx-auto max-w-[1360px] px-6 pb-14 md:px-8">
          <div className="grid gap-8">
            {questionGroups.map((group) => (
              <QuestionSection key={group.title} group={group} />
            ))}
          </div>

          <section className="mt-8 rounded-[1.25rem] border border-[#dccaad] bg-[#fffaf0] px-6 py-5 shadow-[0_10px_24px_rgba(75,55,25,0.05)]">
            <div className="max-w-[1120px]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.28em] text-[#8a6a34]">
                Decision boundary
              </div>
              <p className="mt-4 text-sm leading-7 text-neutral-700">
                VoxaRisk provides structured contract risk intelligence and decision-support observations. It does not verify, approve, certify, guarantee, or replace legal judgment. Users remain responsible for commercial decisions, escalation, negotiation, and professional review where appropriate.
              </p>
            </div>
          </section>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
