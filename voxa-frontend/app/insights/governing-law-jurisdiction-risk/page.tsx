import type { Metadata } from "next";

import { governingLawJurisdictionRiskArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "How to Identify Governing Law and Jurisdiction Risk in Contracts (Before It Costs You) | VoxaRisk Insights",
  description:
    "Learn how to identify governing law, jurisdiction, arbitration seat, and venue risk in contracts before signature. Executive-grade guidance from VoxaRisk on first-pass dispute forum review.",
};

export default function GoverningLawJurisdictionRiskPage() {
  return <InsightArticleLayout article={governingLawJurisdictionRiskArticle} />;
}
