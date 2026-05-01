import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const API_BASE = process.env.VOXA_API_BASE_URL || "http://localhost:8000";
const SESSION_COOKIE = "voxarisk_account_session";

export async function GET(_request: Request, context: { params: Promise<{ scanId: string }> }) {
  try {
    const cookieStore = await cookies();
    const token = cookieStore.get(SESSION_COOKIE)?.value ?? "";
    const { scanId } = await context.params;

    if (!token) {
      return NextResponse.json({ error: "Not signed in." }, { status: 401 });
    }

    const upstream = await fetch(`${API_BASE}/account/scans/${encodeURIComponent(scanId)}`, {
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
      { error: `Scan detail proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
