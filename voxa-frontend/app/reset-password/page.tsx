"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

type TokenState = "checking" | "valid" | "invalid" | "missing";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}
export default function ResetPasswordPage() {
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [tokenState, setTokenState] = useState<TokenState>("checking");
  const [tokenMessage, setTokenMessage] = useState<string | null>(null);

  useEffect(() => {
    const resetToken = (new URLSearchParams(window.location.search).get("token") ?? "").trim();
    setToken(resetToken);

    if (!resetToken) {
      setTokenState("missing");
      setTokenMessage("Reset token missing. Request a fresh password reset link.");
      return;
    }

    let cancelled = false;

    async function validateToken() {
      setTokenState("checking");
      setTokenMessage(null);
      try {
        const response = await fetch("/api/account/password/reset/validate", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ token: resetToken }),
        });

        if (cancelled) {
          return;
        }

        if (response.ok) {
          setTokenState("valid");
          return;
        }

        const payload = await response.json().catch(() => null);
        const code = typeof payload?.code === "string" ? payload.code : "invalid";
        setTokenState("invalid");
        setTokenMessage(
          code === "token_expired" || code === "token_already_used"
            ? "This reset link has expired or has already been used. Request a fresh password reset link."
            : "This reset link is not valid. Request a fresh password reset link.",
        );
      } catch (error) {
        if (!cancelled) {
          setTokenState("invalid");
          setTokenMessage(`Password reset link could not be validated. ${String(error)}`);
        }
      }
    }

    validateToken();

    return () => {
      cancelled = true;
    };
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);

    const resetToken = token.trim();

    if (!resetToken || tokenState !== "valid") {
      setMessage("Request a fresh password reset link before setting a new password.");
      return;
    }

    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    if (password.length < 12) {
      setMessage("Use a password of at least 12 characters.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/account/password/reset/complete", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token: resetToken, password }),
      });

      if (!response.ok) {
        setMessage("Password reset could not be completed. The reset link may be invalid or expired.");
        return;
      }

      window.location.href = "/account";
    } catch (error) {
      setMessage(`Password reset could not be completed. ${String(error)}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <main className="min-h-screen bg-[#f6efe1] text-neutral-950">
        <SiteHeader emphasizeSignIn />
        <section className="mx-auto max-w-[1360px] px-6 py-10 md:px-8">
          <div className="grid gap-8 rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-stretch">
            <div className="flex min-h-[430px] flex-col justify-center">
              <Eyebrow>Controlled reset</Eyebrow>
              <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
                Reset your VoxaRisk password.
              </h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
                Reset links are time-limited and single-use. Completing a reset changes the password only; organisation membership and entitlement remain unchanged.
              </p>
            </div>

            <form onSubmit={onSubmit} className="flex h-full flex-col justify-center rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                Reset password
              </div>

              {tokenState === "checking" && (
                <div className="mt-5 rounded-xl border border-[#d8c49e] bg-[#fffdf8] p-4 text-sm leading-6 text-neutral-700">
                  Checking reset link...
                </div>
              )}

              {(tokenState === "missing" || tokenState === "invalid") && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  <div>{tokenMessage}</div>
                  <Link href="/forgot-password" className="mt-3 inline-flex font-semibold underline-offset-4 hover:underline">
                    Request a fresh reset link
                  </Link>
                </div>
              )}

              <label className="mt-6 text-sm font-semibold text-neutral-900" htmlFor="password">
                New password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                disabled={tokenState !== "valid"}
                className="mt-2 rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]"
                minLength={12}
                required
              />

              <label className="mt-5 text-sm font-semibold text-neutral-900" htmlFor="confirmPassword">
                Confirm password
              </label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                disabled={tokenState !== "valid"}
                className="mt-2 rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]"
                minLength={12}
                required
              />

              {message && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || tokenState !== "valid"}
                className="mt-6 rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Resetting password..." : "Reset password"}
              </button>
            </form>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
