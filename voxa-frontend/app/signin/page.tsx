"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

import PasswordInput from "../password-input";
import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch("/api/account/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        setMessage("Sign in could not be completed. Check the account details and membership status.");
        return;
      }

      window.location.href = "/account";
    } catch (error) {
      setMessage(`Sign in could not be completed. ${String(error)}`);
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
              <Eyebrow>Account identity</Eyebrow>
              <h1 className="mt-6 max-w-4xl text-4xl font-semibold leading-[1.05] tracking-[-0.055em] text-neutral-950 md:text-5xl">
                Sign in to your VoxaRisk account.
              </h1>
              <p className="mt-6 max-w-3xl text-base leading-8 text-neutral-700">
                Sign in to access your VoxaRisk account and organisation workspace. Available
                features depend on your organisation’s subscription and account permissions.
              </p>
            </div>

            <form
              onSubmit={onSubmit}
              className="flex h-full flex-col justify-center rounded-[1.5rem] border border-[#d8c49e] bg-[#fbf3e5] p-7 shadow-[0_16px_36px_rgba(75,55,25,0.08)]"
            >
              <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
                Sign in
              </div>

              <label className="mt-6 text-sm font-semibold text-neutral-900" htmlFor="email">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="mt-2 rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]"
                required
              />

              <label className="mt-5 text-sm font-semibold text-neutral-900" htmlFor="password">
                Password
              </label>
              <PasswordInput
                id="password"
                name="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                className="mt-2 rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none transition focus:border-[#8a6a34]"
                required
              />

              {message && (
                <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-800">
                  {message}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-6 rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17] disabled:cursor-not-allowed disabled:opacity-60"
              >
                {loading ? "Signing in..." : "Sign in"}
              </button>

              <div className="mt-5 flex flex-col gap-3 text-xs leading-6 text-neutral-600">
                <Link href="/forgot-password" className="font-semibold text-[#7b5d2c] underline-offset-4 hover:underline">
                  Forgot password?
                </Link>
                <p>
                  Sign-in does not grant premium access by itself. Organisation
                  entitlement is still resolved from persisted subscription state.
                </p>
              </div>
            </form>
          </div>
        </section>
      </main>
      <SiteFooter />
    </>
  );
}
