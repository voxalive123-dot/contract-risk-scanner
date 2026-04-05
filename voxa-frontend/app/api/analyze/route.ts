import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const API_KEY = process.env.VOXA_API_KEY;

export async function POST(request: Request) {
  try {
    if (!API_KEY) {
      return NextResponse.json(
        { error: "Server API key is not configured." },
        { status: 500 }
      );
    }

    const body = await request.json();
    const text = typeof body?.text === "string" ? body.text : "";

    if (!text.trim()) {
      return NextResponse.json(
        { error: "Contract text is required." },
        { status: 400 }
      );
    }

    const upstream = await fetch(`${API_BASE}/analyze_detailed`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
      },
      body: JSON.stringify({ text }),
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
      { error: `Proxy failure: ${String(error)}` },
      { status: 500 }
    );
  }
}
