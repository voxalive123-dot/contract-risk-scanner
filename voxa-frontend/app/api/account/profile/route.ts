import { proxyToApi, readJson } from "../../proxy";

export async function GET() {
  return proxyToApi("/account/profile");
}

export async function PUT(request: Request) {
  const body = await readJson(request);
  return proxyToApi("/account/profile", { method: "PUT", body: JSON.stringify(body) });
}
