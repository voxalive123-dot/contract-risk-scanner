"use client";

import { useEffect, useMemo, useState } from "react";
import {
  blockedReasonFromStatus,
  DataTable,
  formatDate,
  InternalBlockedState,
  InternalShell,
  LoadingNotice,
  MetricCard,
  Panel,
  RawDataDisclosure,
  readable,
  type BlockedReason,
  type TableColumn,
} from "../internal-ui";

type AuditAction = { id: string; actor_user_id: string; org_id: string | null; target_type: string; target_id: string | null; action_type: string; reason: string | null; before: string | null; after: string | null; created_at: string | null };
type Payload = { actions?: AuditAction[] };
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
function compactJson(value: string | null) { if (!value) return "-"; try { const parsed = JSON.parse(value) as Record<string, unknown>; return Object.entries(parsed).slice(0, 4).map(([key, item]) => `${key}: ${String(item)}`).join("; "); } catch { return value.slice(0, 160); } }
export default function Page() {
  const [actions, setActions] = useState<AuditAction[]>([]); const [message, setMessage] = useState("Loading audit log..."); const [blockedReason, setBlockedReason] = useState<BlockedReason>(null); const [actor, setActor] = useState(""); const [action, setAction] = useState("");
  useEffect(() => { let cancelled = false; loadJson<Payload>("/api/internal/ops/audit").then((payload) => { if (cancelled) return; setActions(payload.actions ?? []); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const filtered = useMemo(() => actions.filter((row) => (!actor || row.actor_user_id.toLowerCase().includes(actor.toLowerCase())) && (!action || row.action_type.toLowerCase().includes(action.toLowerCase()))), [actions, actor, action]);
  const columns: TableColumn<AuditAction>[] = [
    { key: "time", label: "Timestamp", render: (row) => formatDate(row.created_at) },
    { key: "actor", label: "Actor", render: (row) => <span className="break-all">{row.actor_user_id}</span> },
    { key: "action", label: "Action", render: (row) => <span className="font-semibold text-neutral-950">{readable(row.action_type)}</span> },
    { key: "target", label: "Target", render: (row) => <div>{row.target_type}<div className="break-all text-neutral-500">{row.target_id ?? "-"}</div></div> },
    { key: "reason", label: "Reason", render: (row) => row.reason ?? "-" },
    { key: "change", label: "Before / after", className: "min-w-[300px]", render: (row) => <details><summary className="cursor-pointer font-semibold text-[#6f5328]">Change summary</summary><div className="mt-2 rounded-lg border border-[#d2bd96] bg-[#fffaf0] p-3"><div><span className="font-semibold">Before:</span> {compactJson(row.before)}</div><div className="mt-2"><span className="font-semibold">After:</span> {compactJson(row.after)}</div></div></details> },
  ];
  return <InternalShell eyebrow="Audit log" title="Audit control board" subtitle="Every owner/internal action should be reviewable by timestamp, actor, target, reason, and change summary.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{!blockedReason && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-3"><MetricCard label="Audit actions" value={actions.length} /><MetricCard label="Filtered" value={filtered.length} /><MetricCard label="Latest action" value={actions[0] ? readable(actions[0].action_type) : "None"} detail={actions[0] ? formatDate(actions[0].created_at) : undefined} /></div><Panel title="Audit filters"><div className="mt-5 grid gap-3 md:grid-cols-2"><input value={actor} onChange={(event) => setActor(event.target.value)} placeholder="Filter by actor ID" className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" /><input value={action} onChange={(event) => setAction(event.target.value)} placeholder="Filter by action" className="rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" /></div><DataTable columns={columns} rows={filtered} emptyLabel="No audit entries match the current filters." /></Panel><RawDataDisclosure data={{ actions }} /></div>}</InternalShell>;
}
