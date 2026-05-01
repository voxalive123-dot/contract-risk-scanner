import type { Metadata } from "next";

import { auditRightsDataAccessContractRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: auditRightsDataAccessContractRiskArticle.seoTitle,
  description: auditRightsDataAccessContractRiskArticle.metaDescription,
};

export default function AuditRightsDataAccessContractRiskPage() {
  return <InsightArticleLayout article={auditRightsDataAccessContractRiskArticle} />;
}
