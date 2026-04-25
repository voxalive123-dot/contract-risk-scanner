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
        { error: "Sign in is required to use the VoxaRisk dashboard." },
        { status: 401 },
      );
    }

    const contentType = request.headers.get("content-type") || "";

    if (contentType.includes("application/json")) {
      const body = await request.json();
      const text = typeof body?.text === "string" ? body.text : "";

      if (!text.trim()) {
        return NextResponse.json(
          { error: "Contract text is required." },
          { status: 400 },
        );
      }

      const upstream = await fetch(`${API_BASE}/account/analyze_detailed`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accountSession}`,
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
    }

    if (contentType.includes("multipart/form-data")) {
      const formData = await request.formData();
      const file = formData.get("file");

      if (!(file instanceof File)) {
        return NextResponse.json(
          { error: "A file upload is required." },
          { status: 400 },
        );
      }

      const upstreamForm = new FormData();
      upstreamForm.append("file", file, file.name);

      const normalizedType = (file.type || "").toLowerCase();
      let upstreamPath = "";

      if (normalizedType === "application/pdf") {
        upstreamPath = "/analyze_pdf";
      } else if (
        normalizedType === "image/jpeg" ||
        normalizedType === "image/jpg" ||
        normalizedType === "image/png" ||
        normalizedType === "image/webp"
      ) {
        upstreamPath = "/analyze_image";
      } else {
        return NextResponse.json(
          { error: "Unsupported file type. Use PDF, JPG, PNG, or WEBP." },
          { status: 400 },
        );
      }

      const upstream = await fetch(
        `${API_BASE}/account${upstreamPath}`,
        {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accountSession}`,
        },
        body: upstreamForm,
        cache: "no-store",
      });

      const raw = await upstream.text();

      return new NextResponse(raw, {
        status: upstream.status,
        headers: {
          "Content-Type": "application/json",
        },
      });
    }

    return NextResponse.json(
      { error: "Unsupported request content type." },
      { status: 400 },
    );
  } catch (error) {
    return NextResponse.json(
      { error: `Proxy failure: ${String(error)}` },
      { status: 500 },
    );
  }
}
