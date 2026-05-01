import type { Metadata } from "next";

import { policyAwareContractReviewToleranceArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "Policy-Aware Contract Review | VoxaRisk Insights",
  description: "How policy-aware contract review compares findings against organisational tolerance and supports disciplined contract risk escalation.",
};

export default function PolicyAwareContractReviewTolerancePage() {
  return <InsightArticleLayout article={policyAwareContractReviewToleranceArticle} />;
}
