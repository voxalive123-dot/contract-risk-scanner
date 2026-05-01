import type { Metadata } from "next";

import { paymentDelayLateFeesContractRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: paymentDelayLateFeesContractRiskArticle.seoTitle,
  description: paymentDelayLateFeesContractRiskArticle.metaDescription,
};

export default function PaymentDelayLateFeesContractRiskPage() {
  return <InsightArticleLayout article={paymentDelayLateFeesContractRiskArticle} />;
}
