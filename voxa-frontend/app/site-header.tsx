"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

type HeaderItem = "product" | "pricing" | "insights" | "dashboard" | "account";
type AuthMode = "auto" | "authenticated" | "unauthenticated";

const ACTIVE_CLASS =
  "rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]";
const LINK_CLASS =
  "rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950";
const ACCOUNT_BUTTON_CLASS =
  "rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b] transition hover:bg-[#f3e4c6]";

function navClass(isActive: boolean) {
  return isActive ? ACTIVE_CLASS : LINK_CLASS;
}

export default function SiteHeader({
  activeItem,
  authMode = "auto",
  emphasizeSignIn = false,
  className = "",
}: {
  activeItem?: HeaderItem;
  authMode?: AuthMode;
  emphasizeSignIn?: boolean;
  className?: string;
}) {
  const [autoSignedIn, setAutoSignedIn] = useState(false);

  useEffect(() => {
    if (authMode !== "auto") {
      return;
    }

    let cancelled = false;

    async function checkSession() {
      try {
        const response = await fetch("/api/account/me", { cache: "no-store" });
        if (!cancelled) {
          setAutoSignedIn(response.ok);
        }
      } catch {
        if (!cancelled) {
          setAutoSignedIn(false);
        }
      }
    }

    void checkSession();

    return () => {
      cancelled = true;
    };
  }, [authMode]);

  const signedIn = authMode === "auto" ? autoSignedIn : authMode === "authenticated";
  const accountLabel = signedIn ? "Account" : "Sign in";
  const accountHref = signedIn ? "/account" : "/signin";
  const accountIsActive = signedIn && activeItem === "account";
  const accountClass = accountIsActive
    ? ACTIVE_CLASS
    : emphasizeSignIn && !signedIn
      ? "rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]"
      : ACCOUNT_BUTTON_CLASS;

  return (
    <header
      className={`sticky top-0 z-50 border-b border-[#dfd0b6] bg-[#f6efe1]/95 backdrop-blur supports-[backdrop-filter]:bg-[#f6efe1]/90 ${className}`.trim()}
    >
      <div className="mx-auto flex max-w-[1360px] flex-col gap-5 px-5 py-5 md:flex-row md:items-center md:justify-between md:px-8">
        <Link href="/" className="flex items-center justify-center gap-4 md:justify-start">
          <div className="flex h-[76px] w-[76px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
            <img
              src="/brand/voxa-circle-logo.png"
              alt="VOXA"
              className="h-full w-full rounded-full object-cover object-center"
            />
          </div>
          <div className="leading-none">
            <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">
              VOXARISK
            </div>
            <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.16em] text-[#7b5d2c]">
              CONTRACT RISK INTELLIGENCE
            </div>
          </div>
        </Link>

        <nav className="flex flex-wrap items-center gap-3 text-sm text-neutral-700 md:justify-end">
          <Link href="/" className={navClass(activeItem === "product")}>
            Product
          </Link>
          <Link href="/#workflow" className={LINK_CLASS}>
            Workflow
          </Link>
          <Link href="/pricing" className={navClass(activeItem === "pricing")}>
            Pricing
          </Link>
          <Link href="/insights" className={navClass(activeItem === "insights")}>
            Insights
          </Link>
          <Link href="/dashboard" className={navClass(activeItem === "dashboard")}>
            Dashboard
          </Link>
          <Link href={accountHref} className={accountClass}>
            {accountLabel}
          </Link>
        </nav>
      </div>
    </header>
  );
}
