"use client";

import { FormEvent, useMemo, useState } from "react";
import SiteHeader from "../site-header";
import SiteFooter from "../site-footer";

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

      <main className="mx-auto max-w-[1180px] px-5 py-10 md:px-8 md:py-14">
        <section className="rounded-[2rem] border border-[#dfd0b6] bg-[#fffaf0] p-8 shadow-[0_22px_60px_rgba(75,55,25,0.10)] md:p-10">
          <div className="text-[11px] font-semibold uppercase tracking-[0.34em] text-[#8a6a34]">Contact</div>
          <h1 className="mt-5 max-w-4xl text-[34px] font-semibold leading-[1.08] tracking-[-0.05em] text-neutral-950 sm:text-[42px] md:text-[56px]">
            Contact VoxaRisk for product, account, or commercial enquiries.
          </h1>
          <p className="mt-6 max-w-3xl text-sm leading-7 text-neutral-700">
            Use this page for product, account, onboarding, or commercial enquiries.
            Please do not submit confidential contract material through this form.
          </p>
        </section>

        <section className="mt-8 grid items-start gap-8 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="flex flex-col gap-5">
            <aside className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-7 shadow-[0_12px_32px_rgba(75,55,25,0.06)]">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">Before contacting us</div>
              <h2 className="mt-4 text-[26px] font-semibold tracking-[-0.04em] text-neutral-950">Keep the enquiry clear and operational.</h2>
              <div className="mt-5 space-y-4 text-sm leading-7 text-neutral-700">
                <p>For contract risk review, use the dashboard rather than emailing confidential documents. For legal interpretation, obtain qualified professional advice.</p>
                <p>For business onboarding, include your organisation type, expected usage, and whether you need individual, team, or enterprise access.</p>
                <p>Current contact route: <span className="font-semibold text-neutral-950">contact@voxarisk.com</span></p>
              </div>
            </aside>

            <aside className="rounded-[1.5rem] border border-[#dfd0b6] bg-[#fffdf8] p-7 shadow-[0_12px_32px_rgba(75,55,25,0.06)]">
              <div className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[#8a6a34]">What happens next</div>
              <h2 className="mt-4 text-[24px] font-semibold tracking-[-0.04em] text-neutral-950">We use written contact to keep the trail clear.</h2>
              <div className="mt-5 space-y-3 text-sm leading-7 text-neutral-700">
                <p>Commercial and account enquiries should include enough context for routing, but not sensitive contract text.</p>
                <p>Where the issue concerns product access, billing, onboarding, or platform use, keep the subject line specific so the enquiry can be handled cleanly.</p>
                <p>For contract review, the dashboard remains the correct route because it keeps analysis, evidence, and decision boundaries inside the product workflow.</p>
              </div>
            </aside>
          </div>

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
