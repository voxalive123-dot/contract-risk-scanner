"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const DEFAULT_CLASSNAME =
  "rounded-xl border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b] transition hover:bg-[#f3e4c6]";

export default function AccountNavLink({ className = DEFAULT_CLASSNAME }: { className?: string }) {
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function checkSession() {
      try {
        const response = await fetch("/api/account/me", { cache: "no-store" });
        if (!cancelled) {
          setSignedIn(response.ok);
        }
      } catch {
        if (!cancelled) {
          setSignedIn(false);
        }
      }
    }

    checkSession();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Link href={signedIn ? "/account" : "/signin"} className={className}>
      {signedIn ? "Account" : "Sign in"}
    </Link>
  );
}