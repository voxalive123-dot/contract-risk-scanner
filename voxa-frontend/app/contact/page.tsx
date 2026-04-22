"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import SiteFooter from "../site-footer";

function SiteHeader() {
  return (
    <header className="border-b border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] items-center justify-between px-6 py-5 md:px-8">
        <Link href="/" className="flex items-center gap-4">
          <div className="flex h-[76px] w-[76px] shrink-0 items-center justify-center overflow-hidden rounded-full shadow-[0_12px_28px_rgba(75,55,25,0.18)]">
            <img src="/brand/voxa-circle-logo.png" alt="VOXA" className="h-full w-full rounded-full object-cover object-center" />
          </div>
          <div className="leading-none">
            <div className="text-[20px] font-black uppercase tracking-[0.24em] text-neutral-950">VOXARISK</div>
            <div className="mt-2 text-[11px] font-semibold uppercase tracking-[0.32em] text-[#8a6a34]">Contract Risk Intelligence</div>
          </div>
        </Link>

        <nav className="flex items-center gap-4 text-sm font-medium text-neutral-700">
          <Link href="/" className="rounded-full px-3 py-2 transition hover:bg-[#eadcc4] hover:text-neutral-950">Product</Link>
          <Link href="/pricing" className="rounded-full border border-[#c6aa72] bg-[#fff8ea] px-4 py-2 font-semibold text-[#765a2b]">Pricing</Link>
          <Link href="/dashboard" className="rounded-xl bg-[#11110f] px-4 py-2 font-semibold text-stone-100 transition hover:bg-[#1b1a17]">Dashboard</Link>
        </nav>
      </div>
    </header>
  );
}

export default function ContactPage() {
  const [humanCheck, setHumanCheck] = useState("");
  const [status, setStatus] = useState("");
  const challenge = useMemo(() => ({ question: "Security check: what is 7 + 6?", answer: "13" }), []);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("");

    const form = new FormData(event.currentTarget);
    const website = String(form.get("website") || "").trim();

    if (website) {
      setStatus("Submission blocked.");
      return;
    }

    if (humanCheck.trim() !== challenge.answer) {
      setStatus("Please complete the human verification check correctly before sending.");
      return;
    }

    const name = String(form.get("name") || "");
    const email = String(form.get("email") || "");
    const organisation = String(form.get("organisation") || "");
    const subject = String(form.get("subject") || "VoxaRisk enquiry");
    const message = String(form.get("message") || "");

    const body = encodeURIComponent(
      `Name: ${name}\nEmail: ${email}\nOrganisation: ${organisation}\n\nMessage:\n${message}`
    );

    window.location.href = `mailto:contact@voxarisk.com?subject=${encodeURIComponent(subject)}&body=${body}`;
    setStatus("Opening your email client. If it does not open, email contact@voxarisk.com directly.");
  }

  return (
    <div className="min-h-screen bg-[#f4eddf] text-neutral-950">
      <SiteHeader />

      <main className="mx-auto max-w-[1180px] px-6 py-14 md:px-8">
        <section className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[#8a6a34]">Contact</div>
          <h1 className="mt-5 max-w-4xl text-[42px] font-semibold leading-[1.05] tracking-[-0.05em] text-neutral-950 md:text-[56px]">
            Contact VoxaRisk for product, account, or commercial enquiries.
          </h1>
          <p className="mt-6 max-w-3xl text-sm leading-7 text-neutral-700">
            Use this page for product, account, onboarding, or commercial enquiries.
            Please do not submit confidential contract material through this form.
          </p>
        </section>

        <section className="mt-8 grid items-start gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <aside className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-7 shadow-[0_12px_32px_rgba(75,55,25,0.06)]">
            <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Before contacting us</div>
            <h2 className="mt-4 text-[26px] font-semibold tracking-[-0.04em] text-neutral-950">Keep the enquiry clear and operational.</h2>
            <div className="mt-5 space-y-4 text-sm leading-7 text-neutral-700">
              <p>For contract risk review, use the dashboard rather than emailing confidential documents. For legal interpretation, obtain qualified professional advice.</p>
              <p>For business onboarding, include your organisation type, expected usage, and whether you need individual, team, or enterprise access.</p>
              <p>Current contact route: <span className="font-semibold text-neutral-950">contact@voxarisk.com</span></p>
            </div>
          </aside>

          <form onSubmit={handleSubmit} className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-7 shadow-[0_12px_32px_rgba(75,55,25,0.06)]">
            <div className="grid gap-4 md:grid-cols-2">
              <label className="text-sm font-medium text-neutral-800">Name
                <input name="name" required className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
              </label>
              <label className="text-sm font-medium text-neutral-800">Email
                <input name="email" type="email" required className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
              </label>
              <label className="text-sm font-medium text-neutral-800">Organisation
                <input name="organisation" className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
              </label>
              <label className="text-sm font-medium text-neutral-800">Subject
                <input name="subject" required className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
              </label>
            </div>

            <label className="mt-4 block text-sm font-medium text-neutral-800">Message
              <textarea name="message" required rows={7} className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
            </label>

            <input name="website" tabIndex={-1} autoComplete="off" className="hidden" />

            <div className="mt-5 rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-5">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Human verification</div>
              <label className="mt-3 block text-sm font-medium text-neutral-800">{challenge.question}
                <input value={humanCheck} onChange={(event) => setHumanCheck(event.target.value)} required inputMode="numeric" className="mt-2 w-full rounded-xl border border-[#d2bd96] bg-[#fffaf0] px-4 py-3 outline-none focus:border-[#8a6a34]" />
              </label>
            </div>

            {status && <div className="mt-4 rounded-xl border border-[#d2bd96] bg-[#fcf7ee] px-4 py-3 text-sm text-neutral-700">{status}</div>}

            <div className="mt-5 grid gap-3 md:grid-cols-2">
              <div className="rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">Response path</div>
                <p className="mt-2 text-sm leading-6 text-neutral-700">
                  Your enquiry opens through email so there is a clear written trail.
                </p>
              </div>
              <div className="rounded-[1rem] border border-[#d2bd96] bg-[#fcf7ee] p-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[#8a6a34]">Security boundary</div>
                <p className="mt-2 text-sm leading-6 text-neutral-700">
                  Keep messages operational. Use the dashboard for contract review.
                </p>
              </div>
            </div>

            <button type="submit" className="mt-5 rounded-xl bg-[#11110f] px-6 py-3 text-sm font-semibold text-stone-100 transition hover:bg-[#1b1a17]">
              Send enquiry
            </button>
          </form>
        </section>
      </main>

      <SiteFooter />
    </div>
  );
}
