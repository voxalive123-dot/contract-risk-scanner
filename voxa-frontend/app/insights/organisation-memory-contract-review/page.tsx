import type { Metadata } from "next";

import { organisationMemoryContractReviewArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: "Organisation Memory in Contract Review | VoxaRisk Insights",
  description: "Why contract review history, recurring risk families, decision records, and report snapshots strengthen commercial contract governance and audit trails.",
};

export default function OrganisationMemoryContractReviewPage() {
  return <InsightArticleLayout article={organisationMemoryContractReviewArticle} />;
}
