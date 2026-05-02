"use client";

import { useEffect, useState } from "react";
import { InternalShell, Panel } from "../internal-ui";

type JsonRecord = Record<string, unknown>;

export default function Page() {
  const [data, setData] = useState<JsonRecord | null>(null);
  const [message, setMessage] = useState("Loading...");

  useEffect(() => {
    let cancelled = false;
    fetch("/api/internal/ops/summary", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("internal_surface_unavailable");
        return response.json() as Promise<JsonRecord>;
      })
      .then((payload) => {
        if (cancelled) return;
        setData(payload);
        setMessage("");
      })
      .catch(() => {
        if (cancelled) return;
        setMessage("This internal surface is unavailable for this account.");
      });
    return () => { cancelled = true; };
  }, []);

  const preview = data ? data : null;

  return (
    <InternalShell eyebrow="Subscriptions" title="Subscription states.">
      {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
      {data !== null && <Panel title="Live backend data"><pre className="mt-5 max-h-[640px] overflow-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-xs leading-6 text-neutral-700">{JSON.stringify(preview, null, 2)}</pre></Panel>}
    </InternalShell>
  );
}
