import type { Metadata } from "next";

import { contractRiskDecisionIntelligenceBeyondClauseDetectionArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "Contract Risk Decision Intelligence | VoxaRisk Insights",
  description: "Why contract review must move beyond clause detection toward cross-clause interpretation, organisation memory, tolerance comparison, decision history, and audit-ready records.",
};

export default function ContractRiskDecisionIntelligenceBeyondClauseDetectionPage() {
  return <InsightArticleLayout article={contractRiskDecisionIntelligenceBeyondClauseDetectionArticle} />;
}
