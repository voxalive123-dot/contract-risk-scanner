import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

export async function GET(request: Request) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get(SESSION_COOKIE)?.value ?? "";
    if (!token) {
      return NextResponse.json({ error: "Not signed in." }, { status: 401 });
    }

    const url = new URL(request.url);
    const orgId = url.searchParams.get("org_id");
    const path = orgId
      ? `${API_BASE}/internal/ops/organizations/${encodeURIComponent(orgId)}`
      : `${API_BASE}/internal/ops/organizations`;

    const upstream = await fetch(path, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
      cache: "no-store",
    });

    const raw = await upstream.text();
    return new NextResponse(raw, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Internal operations proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}