import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

async function sessionToken() {
  const cookieStore = await cookies();
  return cookieStore.get(SESSION_COOKIE)?.value ?? "";
}

async function proxyJson(path: string, init?: RequestInit) {
  const token = await sessionToken();
  if (!token) {
    return NextResponse.json({ error: "Not signed in." }, { status: 401 });
  }

  const upstream = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  const raw = await upstream.text();
  return new NextResponse(raw, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const email = url.searchParams.get("email");
    if (!email) {
      return NextResponse.json({ error: "email is required." }, { status: 400 });
    }
    return proxyJson(`/internal/ops/user-control?email=${encodeURIComponent(email)}`);
  } catch (error) {
    return NextResponse.json(
      { error: `Internal user control proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const action = typeof body.action === "string" ? body.action : "";
    const email = typeof body.email === "string" ? body.email : "";
    const reason = typeof body.reason === "string" ? body.reason : "";

    if (action === "reset_link") {
      return proxyJson("/internal/ops/user-control/reset-link", {
        method: "POST",
        body: JSON.stringify({ email, reason }),
      });
    }

    if (action === "revoke_invites") {
      return proxyJson("/internal/ops/user-control/revoke-invites", {
        method: "POST",
        body: JSON.stringify({ email, reason }),
      });
    }

    return NextResponse.json({ error: "Unsupported user-control action." }, { status: 400 });
  } catch (error) {
    return NextResponse.json(
      { error: `Internal user control proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
