import { Mascot } from "@/components/Logo";
import { ButtonLink } from "@/components/ui";

export function CtaBand() {
  return (
    <section className="mx-auto max-w-6xl px-5 pt-4">
      <div className="card relative overflow-hidden bg-sun p-10 sm:p-16">
        <div className="pointer-events-none absolute -right-10 -top-10 h-56 w-56 rounded-full bg-coral/70" aria-hidden="true" />
        <div className="pointer-events-none absolute -bottom-16 left-1/3 h-48 w-48 rounded-full bg-sky/70" aria-hidden="true" />
        <div className="relative grid items-center gap-8 md:grid-cols-[1fr_auto]">
          <div>
            <h2 className="text-4xl font-extrabold leading-tight sm:text-6xl">Make your buckets boring again.</h2>
            <p className="mt-4 max-w-xl text-xl text-ink/80">Free while we are in early access. Connect an account in about two minutes.</p>
            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <ButtonLink href="/sign-up" tone="peri" className="px-8 py-4 text-lg">Start free</ButtonLink>
              <ButtonLink href="/demo" tone="white" className="px-8 py-4 text-lg">Play with the demo</ButtonLink>
            </div>
          </div>
          <div className="hidden md:block"><Mascot size={170} /></div>
        </div>
      </div>
    </section>
  );
}
