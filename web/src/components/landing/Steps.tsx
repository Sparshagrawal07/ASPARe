import { LogIn, PlugZap, ShieldCheck } from "lucide-react";
import { SectionHeading } from "@/components/ui";

const STEPS = [
  { icon: LogIn, n: "1", t: "Sign in", d: "Create an account in seconds. No credit card, no cloud keys, nothing to install.", tone: "bg-sun" },
  { icon: PlugZap, n: "2", t: "Connect with one click", d: "ASPARe opens a prefilled stack in your AWS console. You press Create, and the connection turns green by itself.", tone: "bg-sky" },
  { icon: ShieldCheck, n: "3", t: "Relax. We watch.", d: "Every bucket is scanned, explained and ranked. Safe fixes happen automatically if you allow them, and each one is verified.", tone: "bg-mint" },
];

export function Steps() {
  return (
    <section className="bg-peri-100 py-20" aria-labelledby="steps">
      <div className="mx-auto max-w-6xl px-5">
        <SectionHeading
          kicker="Getting started"
          title={<span id="steps">From zero to protected in about two minutes</span>}
          sub="No repository to clone and no scripts to run. Everything happens in your browser."
          center
          tone="sun"
        />
        <ol className="mt-14 grid gap-6 md:grid-cols-3">
          {STEPS.map(({ icon: Icon, ...s }) => (
            <li key={s.n} className="card lift relative bg-white p-7 pt-10">
              <span className={`absolute -top-6 left-6 flex h-12 w-12 items-center justify-center rounded-full border-2 border-ink font-display text-2xl font-extrabold ${s.tone}`}>
                {s.n}
              </span>
              <Icon size={30} strokeWidth={2} aria-hidden="true" />
              <h3 className="mt-4 text-2xl font-extrabold">{s.t}</h3>
              <p className="mt-2 text-[16px] leading-relaxed text-muted">{s.d}</p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
