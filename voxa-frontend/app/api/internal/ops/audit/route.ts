import { proxyToApi } from "../../../proxy";

export async function GET() {
  return proxyToApi("/internal/ops/audit");
}
