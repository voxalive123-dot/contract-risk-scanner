import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

async function sessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get(SESSION_COOKIE)?.value ?? "";
}

export async function POST(
  request: Request,
  context: { params: Promise<{ grantId: string }> },
) {
  try {
    const token = await sessionToken();
    if (!token) {
      return NextResponse.json({ error: "Not signed in." }, { status: 401 });
    }

    const { grantId } = await context.params;
    const body = await request.json();
    const upstream = await fetch(`${API_BASE}/internal/ops/access-grants/${encodeURIComponent(grantId)}/revoke`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const raw = await upstream.text();
    return new NextResponse(raw, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Internal access grants revoke proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
