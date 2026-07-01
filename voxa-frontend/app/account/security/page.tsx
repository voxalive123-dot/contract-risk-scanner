"use client";

import { FormEvent, useState } from "react";
import { AccountShell, ConfirmDialog, Panel, Toast, useToast } from "../account-ui";

export default function AccountSecurityPage() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [closureReason, setClosureReason] = useState("");
  const [pwdLoading, setPwdLoading] = useState(false);
  const [closureLoading, setClosureLoading] = useState(false);
  const [closureConfirmOpen, setClosureConfirmOpen] = useState(false);
  const { toasts, showToast, dismissToast } = useToast();

  async function changePassword(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPwdLoading(true);
    const response = await fetch("/api/account/change-password", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ current_password: currentPassword, new_password: newPassword, confirm_password: confirmPassword }) });
    const payload = await response.json().catch(() => null);
    setPwdLoading(false);
    if (!response.ok) { showToast(typeof payload?.detail === "string" ? payload.detail : "Password could not be changed.", "error"); return; }
    setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
    showToast("Password changed.", "success");
  }

  async function executeClosure() {
    setClosureConfirmOpen(false);
    setClosureLoading(true);
    const response = await fetch("/api/account/closure-request", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ reason: closureReason }) });
    const payload = await response.json().catch(() => null);
    setClosureLoading(false);
    if (!response.ok) { showToast("Closure request could not be submitted.", "error"); return; }
    showToast(payload?.retention_notice ?? "Closure requested.", "success");
  }

  return (
    <>
      <AccountShell eyebrow="Security" title="Password and closure controls.">
        <div className="mt-6 grid gap-6 lg:grid-cols-2">
          <Panel title="Change password">
            <form onSubmit={changePassword} className="mt-5 space-y-3">
              <input type="password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} placeholder="Current password" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
              <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} placeholder="New password" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
              <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} placeholder="Confirm new password" className="w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
              <button type="submit" disabled={pwdLoading} className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 disabled:opacity-60">Change password</button>
            </form>
          </Panel>
          <Panel title="Account closure">
            <p className="mt-5 text-sm leading-7 text-neutral-700">Closure disables the account and records the request. Billing, audit, and scan records are retained for operational integrity.</p>
            <textarea value={closureReason} onChange={(e) => setClosureReason(e.target.value)} placeholder="Optional closure reason" className="mt-4 min-h-28 w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm outline-none focus:border-[#8a6a34]" />
            <button type="button" disabled={closureLoading} onClick={() => setClosureConfirmOpen(true)} className="mt-4 rounded-xl border border-red-300 bg-red-50 px-5 py-3 text-sm font-semibold text-red-900 disabled:opacity-60">
              {closureLoading ? "Submitting…" : "Request closure"}
            </button>
          </Panel>
        </div>
      </AccountShell>

      <ConfirmDialog
        key={closureConfirmOpen ? "dialog-open" : "dialog-closed"}
        open={closureConfirmOpen}
        title="Request account closure"
        description="This will disable sign-in and record the closure request. Critical billing and audit records will be retained."
        requireReason={false}
        onConfirm={() => void executeClosure()}
        onCancel={() => setClosureConfirmOpen(false)}
      />
      <Toast toasts={toasts} onDismiss={dismissToast} />
    </>
  );
}
