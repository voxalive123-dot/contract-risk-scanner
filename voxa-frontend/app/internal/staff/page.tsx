"use client";

import { useEffect, useState } from "react";
import {
  ActionButton,
  blockedReasonFromStatus,
  DataTable,
  EmptyState,
  InternalBlockedState,
  InternalShell,
  LoadingNotice,
  MetricCard,
  Panel,
  PLATFORM_OWNER_EMAIL,
  RawDataDisclosure,
  StatusBadge,
  type BlockedReason,
  type TableColumn,
} from "../internal-ui";

type StaffPayload = { user_id: string; email: string; role: "owner" | "manager" | "assistant" | null; permissions: { read: boolean; manage_users: boolean; manage_testers: boolean; manage_staff: boolean } };
async function loadJson<T>(path: string): Promise<T> { const response = await fetch(path, { cache: "no-store" }); if (!response.ok) throw new Error(blockedReasonFromStatus(response.status) ?? "signin"); return response.json() as Promise<T>; }
type RoleRow = { role: "owner" | "manager" | "assistant"; read: boolean; manageUsers: boolean; manageTesters: boolean; manageStaff: boolean; viewRevenue: boolean; viewAudit: boolean; boundary: string };
const roles: RoleRow[] = [
  { role: "owner", read: true, manageUsers: true, manageTesters: true, manageStaff: true, viewRevenue: true, viewAudit: true, boundary: "Full platform authority for the verified owner identity only." },
  { role: "manager", read: true, manageUsers: true, manageTesters: false, manageStaff: false, viewRevenue: true, viewAudit: true, boundary: "Operational support without owner bypass or staff control." },
  { role: "assistant", read: true, manageUsers: false, manageTesters: false, manageStaff: false, viewRevenue: false, viewAudit: true, boundary: "Read/support visibility only; no destructive controls." },
];
function mark(value: boolean) { return value ? <StatusBadge value="enabled" tone="good" /> : <StatusBadge value="disabled" tone="neutral" />; }
export default function Page() {
  const [staff, setStaff] = useState<StaffPayload | null>(null); const [message, setMessage] = useState("Loading staff authority..."); const [blockedReason, setBlockedReason] = useState<BlockedReason>(null);
  useEffect(() => { let cancelled = false; loadJson<StaffPayload>("/api/internal/ops/staff").then((payload) => { if (cancelled) return; setStaff(payload); setMessage(""); }).catch((error: Error) => { if (cancelled) return; setBlockedReason(error.message === "restricted" ? "restricted" : "signin"); setMessage(""); }); return () => { cancelled = true; }; }, []);
  const columns: TableColumn<RoleRow>[] = [
    { key: "role", label: "Role", render: (row) => <StatusBadge value={row.role} tone={row.role === "owner" ? "owner" : "neutral"} /> },
    { key: "read", label: "Read", render: (row) => mark(row.read) },
    { key: "users", label: "Manage users", render: (row) => mark(row.manageUsers) },
    { key: "testers", label: "Manage testers", render: (row) => mark(row.manageTesters) },
    { key: "staff", label: "Manage staff", render: (row) => mark(row.manageStaff) },
    { key: "revenue", label: "View revenue", render: (row) => mark(row.viewRevenue) },
    { key: "audit", label: "View audit", render: (row) => mark(row.viewAudit) },
    { key: "boundary", label: "Boundary", render: (row) => row.boundary },
  ];
  return <InternalShell eyebrow="Staff roles" title="Staff and authority control board" subtitle="Role boundaries for owner, manager, and assistant access. Owner bypass remains limited to the verified platform owner identity.">{message && <LoadingNotice label={message} />}{blockedReason && <InternalBlockedState reason={blockedReason} />}{staff && <div className="mt-8 space-y-6"><div className="grid gap-4 md:grid-cols-3"><MetricCard label="Current operator" value={staff.email} detail={staff.user_id} /><MetricCard label="Current role" value={<StatusBadge value={staff.role ?? "none"} tone={staff.role === "owner" ? "owner" : "neutral"} />} /><MetricCard label="Owner identity" value={<StatusBadge value="Platform Owner" tone="owner" />} detail={PLATFORM_OWNER_EMAIL} /></div><Panel title="Permission matrix" subtitle="Backend permissions remain authoritative; this matrix documents the operational boundary exposed by the command centre."><DataTable columns={columns} rows={roles} emptyLabel="No staff roles configured." /></Panel><Panel title="Staff assignment"><EmptyState title="Staff assignment backend not yet connected">Role assignment controls are intentionally read-only here until a dedicated backend staff-management endpoint is connected. Do not edit environment staff lists through the frontend.</EmptyState><div className="mt-4 flex flex-wrap gap-2"><ActionButton disabled title="Backend action not connected yet">Add manager</ActionButton><ActionButton disabled title="Backend action not connected yet">Add assistant</ActionButton><ActionButton disabled title="Backend action not connected yet">Revoke staff role</ActionButton></div></Panel><Panel title="Current permission snapshot"><div className="mt-5 grid gap-3 md:grid-cols-4"><MetricCard label="Read" value={mark(staff.permissions.read)} /><MetricCard label="Manage users" value={mark(staff.permissions.manage_users)} /><MetricCard label="Manage testers" value={mark(staff.permissions.manage_testers)} /><MetricCard label="Manage staff" value={mark(staff.permissions.manage_staff)} /></div></Panel><RawDataDisclosure data={staff} /></div>}</InternalShell>;
}
