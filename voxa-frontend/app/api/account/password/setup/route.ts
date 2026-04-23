import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const upstream = await fetch(`${API_BASE}/account/password/setup`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const payload = await upstream.json().catch(() => null);

    if (!upstream.ok) {
      return NextResponse.json(payload ?? { error: "Password setup failed." }, {
        status: upstream.status,
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

    return NextResponse.json({ account: payload.account });
  } catch (error) {
    return NextResponse.json(
      { error: `Account setup proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}