import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="border-t border-[#dfd0b6] bg-[#f6efe1]">
      <div className="mx-auto flex max-w-[1360px] flex-col gap-6 px-6 py-8 text-sm text-neutral-700 md:px-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div>
            <div className="font-semibold tracking-[-0.02em] text-neutral-950">VoxaRisk</div>
            <div className="mt-1 max-w-xl leading-6">
              Automated contract risk intelligence for disciplined commercial review.
              Not legal advice, legal opinion, or contract approval.
            </div>
          </div>

          <nav className="flex flex-wrap gap-x-5 gap-y-2 font-medium">
            <Link href="/terms" className="hover:text-neutral-950">Terms</Link>
            <Link href="/privacy" className="hover:text-neutral-950">Privacy</Link>
            <Link href="/cookies" className="hover:text-neutral-950">Cookies</Link>
            <Link href="/disclaimer" className="hover:text-neutral-950">Disclaimer</Link>
            <Link href="/contact" className="hover:text-neutral-950">Contact</Link>
          </nav>
        </div>

        <div className="border-t border-[#dfd0b6] pt-4 text-xs text-neutral-600">
          © 2026 VoxaRisk. All rights reserved.
        </div>
      </div>
    </footer>
  );
}
