import { cookies } from "next/headers";
import { NextResponse } from "next/server";

const RAW_API_BASE = process.env.VOXA_API_BASE_URL || "http://127.0.0.1:8000";
const SESSION_COOKIE = "voxarisk_account_session";

function resolvedApiBase() {
  try {
    const url = new URL(RAW_API_BASE);
    if (process.env.NODE_ENV !== "production" && url.hostname === "localhost") {
      url.hostname = "127.0.0.1";
    }
    return url.toString().replace(/\/$/, "");
  } catch {
    return RAW_API_BASE.replace(/\/$/, "");
  }
}

function setupErrorPayload(
  code:
    | "invalid_or_expired_token"
    | "password_policy_failed"
    | "setup_service_unavailable"
    | "unexpected_setup_failure",
  detail: string,
) {
  return { code, detail };
}

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const requestPayload = {
      token: typeof body?.token === "string" ? body.token.trim() : body?.token,
      password: body?.password,
    };
    let upstream: Response;
    try {
      upstream = await fetch(`${resolvedApiBase()}/account/password/setup`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(requestPayload),
        cache: "no-store",
      });
    } catch (error) {
      return NextResponse.json(
        setupErrorPayload(
          "setup_service_unavailable",
          `Account setup backend unreachable: ${String(error)}`,
        ),
        { status: 503 },
      );
    }

    const payload = await upstream.json().catch(() => null);

    if (!upstream.ok) {
      const detail =
        typeof payload?.detail === "string"
          ? payload.detail
          : typeof payload?.error === "string"
            ? payload.error
            : "Password setup failed.";

      if (upstream.status === 400) {
        const code =
          detail === "Password setup token is invalid or expired"
            ? "invalid_or_expired_token"
            : "password_policy_failed";
        return NextResponse.json(setupErrorPayload(code, detail), {
          status: upstream.status,
        });
      }

      if (upstream.status === 503) {
        return NextResponse.json(
          setupErrorPayload("setup_service_unavailable", detail),
          {
            status: upstream.status,
          },
        );
      }

      return NextResponse.json(
        setupErrorPayload("unexpected_setup_failure", detail),
        {
          status: upstream.status,
        },
      );
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
      setupErrorPayload(
        "unexpected_setup_failure",
        `Account setup proxy failure: ${String(error)}`,
      ),
      { status: 500 },
    );
  }
}
