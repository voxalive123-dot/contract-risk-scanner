import type { Metadata } from "next";

import { crossClauseIntelligenceHiddenContractExposureArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "Cross-Clause Intelligence | VoxaRisk Insights",
  description: "How cross-clause contract risk analysis identifies hidden contract exposure between liability, indemnity, termination, refund, data, confidentiality, payment, and suspension clauses.",
};

export default function CrossClauseIntelligenceHiddenContractExposurePage() {
  return <InsightArticleLayout article={crossClauseIntelligenceHiddenContractExposureArticle} />;
}
