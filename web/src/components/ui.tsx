"use client";

import { Check, Copy } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { TONE, type Tone } from "./tones";

export type { Tone };

export function ButtonLink({
  href,
  children,
  tone = "peri",
  className = "",
}: {
  href: string;
  children: React.ReactNode;
  tone?: Tone | "white";
  className?: string;
}) {
  const color = tone === "white" ? "bg-white text-ink" : TONE[tone].solid;
  return (
    <Link href={href} className={`btn px-6 py-3 text-[15px] ${color} ${className}`}>
      {children}
    </Link>
  );
}

export function Button({
  tone = "peri",
  className = "",
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone | "white" }) {
  const color = tone === "white" ? "bg-white text-ink" : TONE[tone].solid;
  return <button type="button" {...props} className={`btn px-5 py-2.5 text-[15px] ${color} ${className}`} />;
}

export function Chip({ children, tone = "white", className = "" }: { children: React.ReactNode; tone?: Tone | "white"; className?: string }) {
  const color = tone === "white" ? "bg-white" : TONE[tone].soft;
  return (
    <span className={`inline-flex items-center rounded-full border-2 border-ink px-2.5 py-0.5 text-xs font-bold text-ink ${color} ${className}`}>
      {children}
    </span>
  );
}

export function Switch({
  checked,
  onChange,
  label,
  disabled,
  hint,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  disabled?: boolean;
  hint?: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      title={hint}
      onClick={() => onChange(!checked)}
      className={`flex w-full items-center justify-between gap-3 rounded-xl px-3 py-2 text-left text-[13px] font-medium transition-colors hover:bg-sun-100 disabled:cursor-not-allowed disabled:opacity-50 ${
        checked ? "" : "bg-coral-100"
      }`}
    >
      <span>{label}</span>
      <span aria-hidden="true" className={`relative h-6 w-11 shrink-0 rounded-full border-2 border-ink transition-colors ${checked ? "bg-mint" : "bg-coral"}`}>
        <span className={`absolute top-[1px] h-4 w-4 rounded-full border-2 border-ink bg-white transition-all ${checked ? "left-[22px]" : "left-[2px]"}`} />
      </span>
    </button>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setDone(true);
          setTimeout(() => setDone(false), 1600);
        } catch {
          /* clipboard unavailable: the text stays selectable */
        }
      }}
      className="inline-flex items-center gap-1.5 rounded-lg border-2 border-ink bg-white px-2.5 py-1 text-xs font-bold hover:bg-sun-100"
    >
      {done ? <Check size={14} /> : <Copy size={14} />}
      {done ? "Copied" : label}
    </button>
  );
}

export function CodeBlock({ code, lang = "bash" }: { code: string; lang?: string }) {
  return (
    <div className="overflow-hidden rounded-2xl border-2 border-ink bg-ink">
      <div className="flex items-center justify-between border-b border-paper/15 px-4 py-2">
        <span className="font-mono text-xs text-paper/60">{lang}</span>
        <CopyButton text={code} />
      </div>
      <pre className="overflow-x-auto p-4 font-mono text-[13px] leading-relaxed text-paper">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function SectionHeading({
  kicker,
  title,
  sub,
  center = false,
  tone = "peri",
}: {
  kicker: string;
  title: React.ReactNode;
  sub?: string;
  center?: boolean;
  tone?: Tone;
}) {
  return (
    <div className={center ? "mx-auto max-w-2xl text-center" : "max-w-2xl"}>
      <span className={`inline-block rounded-full border-2 border-ink px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em] text-ink ${TONE[tone].soft}`}>
        {kicker}
      </span>
      <h2 className="mt-4 text-4xl font-extrabold leading-[1.05] sm:text-5xl">{title}</h2>
      {sub && <p className="mt-4 text-lg leading-relaxed text-muted">{sub}</p>}
    </div>
  );
}
