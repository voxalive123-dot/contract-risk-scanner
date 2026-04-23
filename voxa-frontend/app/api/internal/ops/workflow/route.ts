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
    const orgId = url.searchParams.get("org_id");
    if (!orgId) {
      return NextResponse.json({ error: "org_id is required." }, { status: 400 });
    }
    return proxyJson(`/internal/ops/organizations/${encodeURIComponent(orgId)}/workflow`);
  } catch (error) {
    return NextResponse.json(
      { error: `Internal workflow proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const reason = typeof body.reason === "string" ? body.reason : "";

    if (body.type === "operator_note") {
      if (typeof body.org_id !== "string" || !body.org_id) {
        return NextResponse.json({ error: "org_id is required." }, { status: 400 });
      }
      return proxyJson(`/internal/ops/organizations/${encodeURIComponent(body.org_id)}/workflow/notes`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    }

    if (body.type === "cancel_invite") {
      if (typeof body.invite_id !== "string" || !body.invite_id) {
        return NextResponse.json({ error: "invite_id is required." }, { status: 400 });
      }
      return proxyJson(`/internal/ops/invites/${encodeURIComponent(body.invite_id)}/cancel`, {
        method: "POST",
        body: JSON.stringify({ reason }),
      });
    }

    return NextResponse.json({ error: "Unsupported workflow action." }, { status: 400 });
  } catch (error) {
    return NextResponse.json(
      { error: `Internal workflow proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}