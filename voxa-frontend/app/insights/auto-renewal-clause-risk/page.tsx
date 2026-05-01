import type { Metadata } from "next";

import { autoRenewalClauseRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: autoRenewalClauseRiskArticle.seoTitle,
  description: autoRenewalClauseRiskArticle.metaDescription,
};

export default function AutoRenewalClauseRiskPage() {
  return <InsightArticleLayout article={autoRenewalClauseRiskArticle} />;
}
