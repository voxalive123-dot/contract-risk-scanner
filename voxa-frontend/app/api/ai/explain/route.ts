import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.VOXA_API_KEY;

export async function POST(request: Request) {
  try {
    if (!API_KEY) {
      return NextResponse.json(
        {
          status: "unavailable",
          reason: "server_api_key_not_configured",
        },
        { status: 500 },
      );
    }

    const body = await request.json();

    const upstream = await fetch(`${API_BASE}/ai/explain`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
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
