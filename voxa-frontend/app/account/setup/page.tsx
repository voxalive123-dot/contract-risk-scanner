"use client";

import { useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";

import PasswordInput from "../../password-input";
import SiteHeader from "../../site-header";
import SiteFooter from "../../site-footer";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}
function AccountSetupContent() {
  const searchParams = useSearchParams();
  const [token, setToken] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    setToken((searchParams.get("token") ?? "").trim());
  }, [searchParams]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage(null);

    if (password !== confirmPassword) {
      setMessage("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      const response = await fetch("/api/account/password/setup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        const code = typeof payload?.code === "string" ? payload.code : null;
        const detail =
          typeof payload?.detail === "string"
            ? payload.detail
            : typeof payload?.error === "string"
              ? payload.error
              : null;
        setMessage(
          code === "invalid_or_expired_token" ||
            detail === "Password setup token is invalid or expired"
            ? "Account setup could not be completed. The setup link may be invalid or expired."
            : code === "password_policy_failed"
              ? "Account setup could not be completed. Check the password requirements and try again."
              : code === "setup_service_unavailable"
                ? "Account setup service is temporarily unavailable. Confirm the local backend is running and try again."
                : "Account setup could not be completed. Check the setup link and password requirements, then try again.",
        );
        return;
      }

      window.location.href = "/account";
    } catch (error) {
      setMessage(`Account setup could not be completed. ${String(error)}`);
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
              <Eyebrow>Controlled activation</Eyebrow>
              <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
                Set up your VoxaRisk account password.
              </h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
                This activation link confirms access to an operator-provisioned user account.
                It does not create an organisation, alter membership, or grant paid entitlement.
              </p>
            </div>

            <form onSubmit={onSubmit} className="flex h-full flex-col justify-center rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]">
              <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                Password setup
              </div>

              {!token && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  Setup token missing. Use the activation link provided for your account.
                </div>
              )}

              <label className="mt-6 text-sm font-semibold text-neutral-900" htmlFor="password">
                New password
              </label>
              <PasswordInput
                id="password"
                name="password"
                autoComplete="new-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-2 rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]"
                minLength={12}
                required
              />

              <label className="mt-5 text-sm font-semibold text-neutral-900" htmlFor="confirmPassword">
                Confirm password
              </label>
              <PasswordInput
                id="confirmPassword"
                name="confirmPassword"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
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
                disabled={loading || !token}
                className="mt-6 rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Setting password..." : "Set password"}
              </button>

              <p className="mt-5 text-xs leading-6 text-neutral-600">
                Password setup proves account control only. Organisation access remains membership-based, and paid features remain resolver-backed.
              </p>
            </form>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}

export default function AccountSetupPage() {
  return (
    <Suspense fallback={null}>
      <AccountSetupContent />
    </Suspense>
  );
}
