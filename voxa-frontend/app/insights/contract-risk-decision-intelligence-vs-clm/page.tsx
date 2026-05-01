import type { Metadata } from "next";

import { contractRiskDecisionIntelligenceVsClmArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title:
    "Contract Risk Decision Intelligence vs CLM | VoxaRisk Insights",
  description:
    "VoxaRisk is not a traditional CLM platform. Learn how contract risk decision intelligence helps teams identify risk, prioritise negotiation, and make better pre-signature decisions before approval pressure builds.",
};

export default function ContractRiskDecisionIntelligenceVsClmPage() {
  return <InsightArticleLayout article={contractRiskDecisionIntelligenceVsClmArticle} />;
}
