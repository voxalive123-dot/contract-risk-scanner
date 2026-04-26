export type InsightArticle = {
  slug: string;
  category: string;
  title: string;
  summary: string;
  sections: Array<{
    heading: string;
    paragraphs: string[];
  }>;
};

export const firstInsightArticle: InsightArticle = {
  slug: "contract-risk-intelligence-not-legal-advice",
  category: "Product boundary",
  title: "Contract Risk Intelligence Is Not Legal Advice",
  summary:
    "VoxaRisk identifies risk-bearing contract patterns and helps users prioritise review, but it does not provide legal advice, legal opinions, or solicitor services.",
  sections: [
    {
      heading: "What VoxaRisk does",
      paragraphs: [
        "VoxaRisk is a contract risk intelligence and decision-support platform. The platform helps users identify, prioritise, and understand risk-bearing patterns before negotiation or internal review.",
        "It surfaces evidence-backed findings, severity indicators, decision signals, and negotiation priorities so commercial users can structure a first-pass review with more discipline.",
      ],
    },
    {
      heading: "What VoxaRisk does not do",
      paragraphs: [
        "It does not provide legal advice, legal opinions, solicitor services, or contract approval. A scan result is not a legal sign-off and should not be treated as confirmation that a contract is safe to sign.",
        "VoxaRisk does not replace the judgment required to interpret rights, obligations, remedies, dispute exposure, or broader transaction context.",
      ],
    },
    {
      heading: "Why the boundary matters",
      paragraphs: [
        "A contract can contain commercial dependencies, negotiated side arrangements, jurisdiction-specific consequences, or high-value exposure that no first-pass automated review should be treated as resolving on its own.",
        "Keeping the boundary clear helps teams use the platform responsibly: as structured risk intelligence before deeper review, not as a substitute for professional judgment.",
      ],
    },
    {
      heading: "Where the platform helps",
      paragraphs: [
        "VoxaRisk helps teams spot patterns such as broad indemnity, weak termination protection, liability exposure, consequential loss issues, service discretion, and one-sided pricing rights without forcing users through an unstructured read of the whole document.",
        "That makes it useful for triage, internal escalation discipline, negotiation preparation, and executive reporting before a contract moves further through approval.",
      ],
    },
    {
      heading: "When to escalate",
      paragraphs: [
        "Where legal rights, obligations, disputes, or high-value exposure are involved, users should seek appropriate professional advice. The same applies where the contract affects regulated activity, material liability, dispute positioning, or strategic commercial dependency.",
        "Use the platform to narrow attention, not to avoid escalation where the consequence is meaningful.",
      ],
    },
    {
      heading: "Using VoxaRisk responsibly",
      paragraphs: [
        "Use VoxaRisk to structure your first-pass review before escalation. Start with the decision signal, inspect the evidence, understand which findings drive exposure, and decide whether the issue belongs in negotiation, internal approval, or professional review.",
        "VoxaRisk supports review discipline. It does not replace professional legal advice.",
      ],
    },
  ],
};

export const secondInsightArticle: InsightArticle = {
  slug: "first-pass-contract-risk-intelligence",
  category: "Market positioning",
  title: "First-Pass Contract Risk Intelligence: The Gap Between LCM and AI Review",
  summary:
    "Legal Contract Management (LCM) platforms help manage contract processes. AI contract review firms can support deeper review. VoxaRisk fills the early-stage gap: fast, rules-based contract risk intelligence that helps users identify exposure, evidence, and negotiation priorities before heavier review routes.",
  sections: [
    {
      heading: "The two common routes",
      paragraphs: [
        "Legal Contract Management (LCM) platforms usually focus on contract lifecycle management: storage, workflow, approvals, templates, obligations, renewals, and process administration. AI contract review businesses and AI contract review firms often focus on broader or deeper review workflows, document analysis, legal operations support, or human-assisted review.",
        "Both routes can be valuable. But they are not always the fastest or most cost-efficient first step when a business simply needs to know where the commercial contract risk sits.",
      ],
    },
    {
      heading: "Where LCM platforms can lag",
      paragraphs: [
        "An LCM platform can be process-heavy. It may require implementation, onboarding, configuration, data migration, templates, approvals, or operational change before the organisation gets full value from it.",
        "That does not make LCM weak; it reflects its purpose. Its strength is contract lifecycle management and control, not necessarily immediate clause risk detection. Many organisations benefit more from LCM after they already understand what their contract workflow needs.",
      ],
    },
    {
      heading: "Where AI review firms can lag",
      paragraphs: [
        "AI contract review firms can support deeper analysis, specialist workflows, or human-assisted review. The trade-off is that they may involve higher cost, more human involvement, longer turnaround, provider dependency, and broader engagement setup.",
        "Some AI-assisted contract review models also lean heavily on generative outputs unless the process is strongly evidence-governed. For many early-stage reviews, the immediate business need is simpler: what is risky, where is the clause, how severe is it, and what should be escalated.",
      ],
    },
    {
      heading: "The gap VoxaRisk fills",
      paragraphs: [
        "VoxaRisk fills that early-stage gap with fast first-pass contract risk intelligence. It detects risk-bearing contract patterns, produces evidence-backed contract review findings, shows severity indicators, and supports negotiation priorities before the contract moves into heavier review routes.",
        "That helps executives and commercial teams decide whether a contract is routine, negotiable, risky, or worth legal escalation. For many first-pass reviews, VoxaRisk can provide structured risk intelligence at a fraction of the cost and time of heavier review routes.",
      ],
    },
    {
      heading: "Rules-based intelligence before AI explanation",
      paragraphs: [
        "VoxaRisk is not built on AI buzzwords alone. The core assessment is rules-based contract analysis and evidence-governed contract risk scoring. Clause risk detection, severity indicators, and core findings are produced by deterministic logic and risk rules.",
        "AI is used as an explanation layer where available: to help users understand results, not to override the engine’s score, severity, or evidence. In VoxaRisk, AI explains the result; it does not control the result.",
      ],
    },
    {
      heading: "Why executives prefer a first-pass intelligence layer",
      paragraphs: [
        "Executives need speed, clarity, and prioritisation. They need to know what to redline first, what deserves escalation, and what can be handled commercially without sending every agreement into a slow or expensive process.",
        "A first-pass contract review layer protects time, budget, and negotiation leverage. It also helps teams use lawyers, LCM platforms, and AI contract review providers more intelligently by narrowing attention before deeper review begins.",
      ],
    },
    {
      heading: "What VoxaRisk does not replace",
      paragraphs: [
        "VoxaRisk does not replace lawyers, legal advice, solicitor review, LCM platforms, or specialist AI contract review services. It sits before them as a disciplined first-pass risk intelligence layer for executive decision support and contract review automation.",
        "Where legal rights, disputes, regulated matters, or high-value exposure are involved, users should seek appropriate professional advice.",
      ],
    },
  ],
};

export const insightArticles: InsightArticle[] = [firstInsightArticle, secondInsightArticle];

export const futureInsightTopics = [
  "Liability caps and unlimited exposure",
  "Consequential loss clauses",
  "Indemnity clauses",
  "Termination rights",
  "Executive approval discipline",
];
