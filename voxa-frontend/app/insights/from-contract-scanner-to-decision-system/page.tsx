import type { Metadata } from "next";

import { fromContractScannerToDecisionSystemArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "From Contract Scanner to Decision System | VoxaRisk Insights",
  description: "How decision outcomes, finding statuses, audit trails, executive reporting, and privacy-governed intelligence move contract review beyond generic scanning.",
};

export default function FromContractScannerToDecisionSystemPage() {
  return <InsightArticleLayout article={fromContractScannerToDecisionSystemArticle} />;
}
