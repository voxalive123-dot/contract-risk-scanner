import { proxyToApi } from "../../../proxy";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const search = url.searchParams.get("search");
  const suffix = search ? `?search=${encodeURIComponent(search)}` : "";
  return proxyToApi(`/internal/ops/users${suffix}`);
}
