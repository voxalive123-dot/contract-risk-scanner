import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

export async function POST(request: Request) {
  try {
    const cookieStore = await cookies();
    const accountSession = cookieStore.get(SESSION_COOKIE)?.value ?? "";

    if (!accountSession) {
      return NextResponse.json(
        {
          status: "denied",
          reason: "account_session_required",
        },
        { status: 401 },
      );
    }

    const body = await request.json();

    const upstream = await fetch(`${API_BASE}/account/ai/explain`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${accountSession}`,
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const raw = await upstream.text();

    return new NextResponse(raw, {
      status: upstream.status,
      headers: {
        "Content-Type": "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      {
        status: "unavailable",
        reason: "proxy_error",
        error: String(error),
      },
      { status: 500 },
    );
  }
}
