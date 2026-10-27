import { BadgeCheck, HandHeart } from "lucide-react";
import { Chip, SectionHeading } from "@/components/ui";

export function WhyHeld() {
  return (
    <section className="bg-coral-100 py-20" aria-labelledby="held">
      <div className="mx-auto grid max-w-6xl items-center gap-12 px-5 lg:grid-cols-2">
        <div>
          <SectionHeading
            kicker="The difference"
            title={<span id="held">A severity-only tool would have broken your website</span>}
            sub="Two buckets, the same finding. One holds student transcripts, the other is a public marketing site. ASPARe tells them apart and shows its reasoning."
            tone="coral"
          />
          <ul className="mt-8 space-y-3 text-[17px]">
            {["Reasons are shown with every decision, never hidden in a score.", "Confidence is an evidence-weighted estimate and is labelled as one.", "A human approval is always one click away."].map((t) => (
              <li key={t} className="flex items-start gap-3">
                <BadgeCheck className="mt-0.5 shrink-0 text-ok" size={22} aria-hidden="true" />
                {t}
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-5" aria-label="Example decisions from the live engine">
          <article className="card rotate-1 bg-white p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="coral">CRITICAL</Chip>
              <Chip tone="mint">Auto-fix</Chip>
              <span className="font-mono text-sm font-bold">ferpa-transcripts-prod</span>
            </div>
            <p className="mt-3 text-[15px] text-muted">Public Access Block disabled by <b className="text-ink">root at 03:00 UTC</b>, then two more buckets within ten minutes.</p>
            <div className="mt-4 h-3 overflow-hidden rounded-full border-2 border-ink bg-white" role="img" aria-label="Confidence 99 percent">
              <div className="h-full w-[99%] bg-mint" />
            </div>
            <p className="mt-2 text-sm text-muted">Regulated data plus anomalous burst: fixed immediately, then verified.</p>
          </article>
          <article className="card -rotate-1 bg-white p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone="coral">CRITICAL</Chip>
              <Chip tone="sun"><HandHeart size={13} className="mr-1" aria-hidden="true" />Held for a human</Chip>
              <span className="font-mono text-sm font-bold">campus-marketing-site</span>
            </div>
            <p className="mt-3 text-[15px] text-muted">Same finding, but tagged <b className="text-ink">DataClass=PUBLIC, marketing</b>. Public readability is probably the point.</p>
            <div className="mt-4 h-3 overflow-hidden rounded-full border-2 border-ink bg-white" role="img" aria-label="Confidence 52 percent">
              <div className="h-full w-[52%] bg-sun" />
            </div>
            <p className="mt-2 text-sm text-muted">Rule-only tools: auto-fix. ASPARe: ask the owner first.</p>
          </article>
        </div>
      </div>
    </section>
  );
}
