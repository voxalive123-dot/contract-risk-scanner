import type { Metadata } from "next";

import { ipOwnershipBroadLicenceResidualKnowledgeArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export const metadata: Metadata = {
  title: ipOwnershipBroadLicenceResidualKnowledgeArticle.seoTitle,
  description: ipOwnershipBroadLicenceResidualKnowledgeArticle.metaDescription,
};

export default function IpOwnershipBroadLicenceResidualKnowledgePage() {
  return <InsightArticleLayout article={ipOwnershipBroadLicenceResidualKnowledgeArticle} />;
}
