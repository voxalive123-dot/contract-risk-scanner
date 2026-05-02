"use client";

import { useEffect, useState } from "react";
import { InternalBlockedState, InternalShell, Panel } from "../internal-ui";

type JsonRecord = Record<string, unknown>;
type BlockedReason = "signin" | "restricted" | null;

function blockedReasonFromStatus(status: number): BlockedReason {
  if (status === 401) return "signin";
  if (status === 403) return "restricted";
  return "signin";
}

export default function Page() {
  const [data, setData] = useState<JsonRecord | null>(null);
  const [message, setMessage] = useState("Loading...");
  const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);

  useEffect(() => {
    let cancelled = false;
    fetch("/api/internal/ops/summary", { cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) {
          const reason = blockedReasonFromStatus(response.status);
          throw new Error(reason ?? "signin");
        }
        return response.json() as Promise<JsonRecord>;
      })
      .then((payload) => {
        if (cancelled) return;
        setData(payload);
        setMessage("");
        setBlockedReason(null);
      })
      .catch((error: Error) => {
        if (cancelled) return;
        setBlockedReason(error.message === "restricted" ? "restricted" : "signin");
        setMessage("");
      });
    return () => { cancelled = true; };
  }, []);

  const preview = data ? data : null;

  return (
    <InternalShell eyebrow="Scans" title="Scan operations.">
      {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
      {blockedReason && <InternalBlockedState reason={blockedReason} />}
      {data !== null && <Panel title="Live backend data"><pre className="mt-5 max-h-[640px] overflow-auto rounded-xl border border-[#d2bd96] bg-[#fffdf8] p-4 text-xs leading-6 text-neutral-700">{JSON.stringify(preview, null, 2)}</pre></Panel>}
    </InternalShell>
  );
}
