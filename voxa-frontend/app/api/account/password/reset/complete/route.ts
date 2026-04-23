import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const bodyObject: Record<string, unknown> =
      typeof body === "object" && body !== null ? body : {};
    const requestPayload = {
      token: typeof bodyObject.token === "string" ? bodyObject.token.trim() : bodyObject.token,
      password: bodyObject.password,
    };
    let upstream: Response;
    try {
      upstream = await fetch(`${API_BASE}/account/password/reset/complete`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
        cache: "no-store",
      });
    } catch (error) {
      return NextResponse.json(
        { error: `Password reset backend unreachable: ${String(error)}` },
        { status: 503 },
      );
    }

    const raw = await upstream.text();
    const payload = raw ? JSON.parse(raw) : null;

    if (!upstream.ok) {
      return new NextResponse(raw || JSON.stringify(payload ?? {}), {
        status: upstream.status,
        headers: {
          "Content-Type": upstream.headers.get("Content-Type") || "application/json",
        },
      });
    }

    const token = typeof payload?.access_token === "string" ? payload.access_token : "";
    if (!token) {
      return NextResponse.json(
        { error: "Account session was not returned." },
        { status: 502 },
      );
    }

    const cookieStore = await cookies();
    cookieStore.set(SESSION_COOKIE, token, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      path: "/",
      maxAge: 60 * 60 * 8,
    });

    return new NextResponse(raw, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Password reset proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
