import { prepareContractArticle } from "../insights-data";
import { InsightArticleLayout } from "../insights-layout";

export default function PrepareContractInternalReviewPage() {
  return <InsightArticleLayout article={prepareContractArticle} />;
}
