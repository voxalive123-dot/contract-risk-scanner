import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const bodyObject: Record<string, unknown> =
      typeof body === "object" && body !== null ? body : {};
    const requestPayload = {
      token: typeof bodyObject.token === "string" ? bodyObject.token.trim() : bodyObject.token,
    };

    let upstream: Response;
    try {
      upstream = await fetch(`${API_BASE}/account/password/reset/validate`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
        cache: "no-store",
      });
    } catch (error) {
      return NextResponse.json(
        { error: `Password reset validation backend unreachable: ${String(error)}` },
        { status: 503 },
      );
    }

    const raw = await upstream.text();
    return new NextResponse(raw, {
      status: upstream.status,
      headers: {
        "Content-Type": upstream.headers.get("Content-Type") || "application/json",
      },
    });
  } catch (error) {
    return NextResponse.json(
      { error: `Password reset validation proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
