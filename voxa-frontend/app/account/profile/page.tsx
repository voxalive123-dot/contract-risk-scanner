"use client";

import { FormEvent, useEffect, useState } from "react";
import { AccountShell, Panel } from "../account-ui";

const fields = [
  ["legal_first_name", "First name (legal)", "legal"],
  ["legal_last_name", "Last name (legal)", "legal"],
  ["business_company_name", "Business/company name", "legal"],
  ["role_title", "Role/title", "legal"],
  ["country", "Country", "legal"],
  ["business_email", "Business email", "business"],
  ["website", "Website", "business"],
  ["address", "Address", "business"],
  ["business_category", "Business category/type", "business"],
  ["display_name", "Display name", "display"],
  ["workspace_name", "Screen/workspace name", "display"],
] as const;

type Profile = Record<(typeof fields)[number][0], string | null> & { legal_identity_complete: boolean; identity_notice: string };

export default function AccountProfilePage() {
  const [profile, setProfile] = useState<Partial<Profile>>({});
  const [message, setMessage] = useState("Loading profile...");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetch("/api/account/profile", { cache: "no-store" })
      .then(async (response) => { if (!response.ok) throw new Error(); return response.json(); })
      .then((data) => { setProfile(data.profile ?? {}); setMessage(""); })
      .catch(() => setMessage("Profile is unavailable for this account."));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage("");
    const response = await fetch("/api/account/profile", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(profile) });
    const payload = await response.json().catch(() => null);
    setSaving(false);
    if (!response.ok) { setMessage(typeof payload?.detail === "string" ? payload.detail : "Profile could not be saved."); return; }
    setProfile(payload.profile ?? profile);
    setMessage("Profile saved.");
  }

  function group(name: string) {
    return fields.filter(([, , section]) => section === name);
  }

  return <AccountShell eyebrow="Profile" title="Identity profile.">
    {message && <div className="mt-6 rounded-xl border border-[#d8c49e] bg-[#fbf3e5] p-5 text-sm text-neutral-700">{message}</div>}
    <form onSubmit={save} className="mt-6 grid gap-6 lg:grid-cols-3">
      {[["legal", "Legal identity"], ["business", "Business profile"], ["display", "Display profile"]].map(([key, title]) => <Panel key={key} title={title}><div className="mt-5 space-y-3">{group(key).map(([field, label]) => <label key={field} className="block text-sm font-semibold text-neutral-800">{label}<input value={(profile[field] as string | null) ?? ""} onChange={(event) => setProfile((current) => ({ ...current, [field]: event.target.value }))} className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffdf8] px-4 py-3 text-sm font-normal outline-none focus:border-[#8a6a34]" /></label>)}</div>{key === "legal" && <p className="mt-4 text-xs leading-6 text-neutral-600">Legal identity is required and remains the billing and compliance truth. Display names are never used for billing or compliance.</p>}</Panel>)}
      <div className="lg:col-span-3"><button type="submit" disabled={saving} className="rounded-xl bg-[#11110f] px-5 py-3 text-sm font-semibold text-stone-100 disabled:opacity-60">{saving ? "Saving..." : "Save profile"}</button></div>
    </form>
  </AccountShell>;
}
