import type { Metadata } from "next";

import { autoRenewalRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "Auto-Renewal Clauses in Contracts: The Hidden Risk That Keeps You Paying | VoxaRisk Insights",
  description:
    "Learn how auto-renewal clauses, notice windows, renewal pricing, and asymmetric termination rights create hidden contract cost exposure before signature and before renewal.",
};

export default function AutoRenewalContractRiskPage() {
  return <InsightArticleLayout article={autoRenewalRiskArticle} />;
}
