import { BadgeCheck, BrainCircuit, Globe, KeyRound, Radar, ShieldCheck, type LucideIcon } from "lucide-react";
import SpotlightCard from "@/components/reactbits/SpotlightCard";
import { TONE, type Tone } from "@/components/tones";
import { SectionHeading } from "@/components/ui";

const FEATURES: { icon: LucideIcon; t: string; d: string; tone: Tone; glow: string }[] = [
  { icon: Globe, t: "One brain, three clouds", d: "AWS S3, Azure Blob and Google Cloud Storage share the same rules, safety gate and verification.", tone: "sky", glow: "rgba(76,195,255,0.28)" },
  { icon: BrainCircuit, t: "Knows when not to fix", d: "A public marketing site is not a leak. ASPARe weighs context and holds the fix for a human when exposure may be intended.", tone: "lilac", glow: "rgba(181,140,255,0.3)" },
  { icon: Radar, t: "Spots suspicious changes", d: "Root credentials, bursts across buckets, odd hours, first-time actors. Behaviour raises priority and groups incidents.", tone: "coral", glow: "rgba(255,107,87,0.26)" },
  { icon: BadgeCheck, t: "Verified, never assumed", d: "After every fix ASPARe re-reads the bucket and re-runs the rule that fired. If it is still wrong, it says so.", tone: "mint", glow: "rgba(46,211,160,0.28)" },
  { icon: ShieldCheck, t: "Hard safety rails", d: "Fixes only touch buckets you allow. Context can lower an automatic action to an alert, never the reverse.", tone: "sun", glow: "rgba(255,200,61,0.34)" },
  { icon: KeyRound, t: "Least privilege, shown", d: "See the exact permissions the role grants before you create it. Delete the stack and access ends immediately.", tone: "pink", glow: "rgba(255,143,184,0.3)" },
];

export function Features() {
  return (
    <section className="mx-auto max-w-6xl px-5 py-20" aria-labelledby="features">
      <SectionHeading
        kicker="What you get"
        title={<span id="features">Serious security, explained like a human</span>}
        sub="Built for the person who has to decide, not just the tool that has to alert."
        tone="lilac"
      />
      <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map(({ icon: Icon, ...f }) => (
          <SpotlightCard key={f.t} theme="light" spotlightColor={f.glow} className="h-full !border-2 !border-ink p-6 shadow-pop">
            <div className={`inline-flex h-14 w-14 items-center justify-center rounded-2xl border-2 border-ink ${TONE[f.tone].solid}`}>
              <Icon size={26} strokeWidth={2.1} aria-hidden="true" />
            </div>
            <h3 className="mt-5 text-2xl font-extrabold">{f.t}</h3>
            <p className="mt-2 text-[16px] leading-relaxed text-muted">{f.d}</p>
          </SpotlightCard>
        ))}
      </div>
    </section>
  );
}
