"use client";

import { ArrowRight, BadgeCheck, ShieldAlert } from "lucide-react";
import BlurText from "@/components/reactbits/BlurText";
import CountUp from "@/components/reactbits/CountUp";
import Magnet from "@/components/reactbits/Magnet";
import { Mascot } from "@/components/Logo";
import { ButtonLink } from "@/components/ui";

const STATS = [
  { to: 3, label: "clouds, one engine", suffix: "", tone: "bg-peri-100" },
  { to: 5, label: "storage controls", suffix: "", tone: "bg-mint-100" },
  { to: 95, label: "automated tests", suffix: "+", tone: "bg-sun-100" },
  { to: 100, label: "fixes re-read from the cloud", suffix: "%", tone: "bg-coral-100" },
];

function Squiggle() {
  return (
    <svg viewBox="0 0 300 18" className="absolute -bottom-2 left-0 h-4 w-full" aria-hidden="true" preserveAspectRatio="none">
      <path d="M3 11c20-12 30 10 50 0s30-10 50 0 30 10 50 0 30-10 50 0 30 10 50 0 30-10 44-2" fill="none" stroke="#ff6b57" strokeWidth="5" strokeLinecap="round" />
    </svg>
  );
}

export function Hero() {
  return (
    <section className="relative overflow-hidden">
      <div className="pointer-events-none absolute -right-24 -top-24 h-[420px] w-[420px] rounded-full bg-sun/60" aria-hidden="true" />
      <div className="pointer-events-none absolute -left-20 bottom-10 h-56 w-56 rounded-full bg-sky/40" aria-hidden="true" />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-5 pb-16 pt-14 lg:grid-cols-[1.15fr_1fr] lg:pt-20">
        <div>
          <span className="inline-flex -rotate-2 items-center gap-2 rounded-full border-2 border-ink bg-mint px-4 py-1.5 text-sm font-extrabold">
            <span className="h-2.5 w-2.5 rounded-full bg-ink" aria-hidden="true" />
            Free during early access
          </span>
          <h1 className="mt-6 text-[2.9rem] font-extrabold leading-[0.98] sm:text-7xl">
            <BlurText text="Your cloud storage," delay={80} animateBy="words" direction="top" className="!justify-start" />
            <span className="relative mt-1 inline-block">
              <BlurText text="finally looks after itself." delay={80} animateBy="words" direction="top" className="!justify-start" color="#4a58e8" />
              <Squiggle />
            </span>
          </h1>
          <p className="mt-8 max-w-xl text-xl leading-relaxed text-muted">
            Sign in, connect your cloud account with one click, and ASPARe watches every bucket, explains what is risky in
            plain words, fixes what is safe to fix, and <strong className="text-ink">proves it worked</strong>.
          </p>
          <div className="mt-9 flex flex-col gap-4 sm:flex-row sm:items-center">
            <Magnet magnetStrength={4} padding={50}>
              <ButtonLink href="/sign-up" tone="coral" className="px-8 py-4 text-lg">
                Start free <ArrowRight size={20} aria-hidden="true" />
              </ButtonLink>
            </Magnet>
            <ButtonLink href="/demo" tone="white" className="px-8 py-4 text-lg">
              Try it without signing up
            </ButtonLink>
          </div>
          <p className="mt-5 text-sm font-medium text-muted">No cloud keys stored. Read-only unless you say otherwise.</p>
        </div>

        <div className="relative mx-auto w-full max-w-md" aria-label="Illustration: an exposed bucket becomes a protected bucket">
          <div className="card float -rotate-2 bg-coral-100 p-5" style={{ ["--r" as string]: "-2deg" }}>
            <div className="flex items-center gap-2">
              <ShieldAlert size={20} className="text-bad" aria-hidden="true" />
              <span className="text-xs font-extrabold uppercase tracking-wider text-bad">Exposed</span>
            </div>
            <p className="mt-2 font-mono text-sm font-bold">student-transcripts-prod</p>
            <p className="mt-1 text-sm text-muted">Public access block switched off by root at 03:00 UTC.</p>
          </div>
          <div className="relative z-10 -mt-3 ml-10 mr-0 rotate-2 pb-8">
            <div className="card bg-mint-100 p-5">
              <div className="flex items-center gap-2">
                <BadgeCheck size={20} className="text-ok" aria-hidden="true" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-ok">Fixed and verified</span>
              </div>
              <p className="mt-2 font-mono text-sm font-bold">student-transcripts-prod</p>
              <p className="mt-1 text-sm text-muted">Re-read from the cloud: all four public-access flags are on.</p>
            </div>
          </div>
          <div className="absolute -bottom-14 right-2 z-20">
            <Mascot size={118} mood="wink" />
          </div>
          <div className="absolute -right-3 -top-6 -rotate-6 rounded-xl border-2 border-ink bg-sun px-3 py-1.5 text-sm font-extrabold shadow-pop">
            0 keys stored
          </div>
        </div>
      </div>

      <dl className="relative mx-auto grid max-w-6xl grid-cols-2 gap-4 px-5 pb-16 sm:grid-cols-4">
        {STATS.map((s) => (
          <div key={s.label} className={`card-flat ${s.tone} px-5 py-5`}>
            <dd className="font-display text-5xl font-extrabold">
              <CountUp to={s.to} duration={1.6} />
              {s.suffix}
            </dd>
            <dt className="mt-1 text-sm font-medium text-muted">{s.label}</dt>
          </div>
        ))}
      </dl>
    </section>
  );
}
