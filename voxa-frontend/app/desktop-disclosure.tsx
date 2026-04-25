"use client";

import { ReactNode, useState } from "react";

type DesktopDisclosureProps = {
  id?: string;
  eyebrow: string;
  title: string;
  intro?: string;
  defaultDesktopOpen?: boolean;
  className?: string;
  children: ReactNode;
};

function Eyebrow({ children }: { children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-[11px] font-semibold uppercase tracking-[0.3em] text-[#8a6a34]">
      <span className="h-px w-8 bg-[#b08d57]" />
      {children}
    </div>
  );
}

export default function DesktopDisclosure({
  id,
  eyebrow,
  title,
  intro,
  defaultDesktopOpen = false,
  className = "",
  children,
}: DesktopDisclosureProps) {
  const [isOpen, setIsOpen] = useState(defaultDesktopOpen);

  return (
    <section id={id} className={className}>
      <div className="lg:hidden">
        <Eyebrow>{eyebrow}</Eyebrow>
        <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
          {title}
        </h2>
        {intro ? <p className="mt-5 max-w-4xl text-base leading-8 text-neutral-700">{intro}</p> : null}
        <div className="mt-8">{children}</div>
      </div>

      <div className="hidden lg:block">
        <button
          type="button"
          onClick={() => setIsOpen((current) => !current)}
          aria-expanded={isOpen}
          className="flex w-full items-start justify-between gap-6 text-left"
        >
          <div>
            <Eyebrow>{eyebrow}</Eyebrow>
            <h2 className="mt-5 text-[28px] font-semibold tracking-[-0.04em] text-neutral-950">
              {title}
            </h2>
            {intro ? (
              <p className="mt-4 max-w-4xl text-sm leading-7 text-neutral-700">{intro}</p>
            ) : null}
          </div>
          <span className="mt-1 flex shrink-0 items-center gap-3 rounded-full border border-[#d3bd8f] bg-[#fff4dc] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#8a6a34]">
            <span className="text-sm leading-none">{isOpen ? "−" : "+"}</span>
            <span>{isOpen ? "Collapse" : "Expand"}</span>
          </span>
        </button>

        {isOpen ? <div className="mt-8">{children}</div> : null}
      </div>
    </section>
  );
}
