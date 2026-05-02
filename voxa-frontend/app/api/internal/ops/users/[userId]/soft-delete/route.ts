import { proxyToApi, readJson } from "../../../../../proxy";

type Params = { params: Promise<{ userId: string }> };

export async function POST(request: Request, { params }: Params) {
  const { userId } = await params;
  const body = await readJson(request);
  return proxyToApi(`/internal/ops/users/${encodeURIComponent(userId)}/soft-delete`, { method: "POST", body: JSON.stringify(body) });
}
