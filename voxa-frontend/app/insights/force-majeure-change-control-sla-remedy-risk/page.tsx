import type { Metadata } from "next";

import { forceMajeureChangeControlSlaRemedyRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: forceMajeureChangeControlSlaRemedyRiskArticle.seoTitle,
  description: forceMajeureChangeControlSlaRemedyRiskArticle.metaDescription,
};

export default function ForceMajeureChangeControlSlaRemedyRiskPage() {
  return <InsightArticleLayout article={forceMajeureChangeControlSlaRemedyRiskArticle} />;
}
