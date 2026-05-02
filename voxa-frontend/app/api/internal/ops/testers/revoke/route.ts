import { proxyToApi, readJson } from "../../../../proxy";

export async function POST(request: Request) {
  const body = await readJson(request);
  return proxyToApi("/internal/ops/testers/revoke", { method: "POST", body: JSON.stringify(body) });
}
