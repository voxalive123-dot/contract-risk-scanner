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

export const insightArticles: InsightArticle[] = [firstInsightArticle];

export const futureInsightTopics = [
  "Liability caps and unlimited exposure",
  "Consequential loss clauses",
  "Indemnity clauses",
  "Termination rights",
  "AI-assisted contract review",
];
