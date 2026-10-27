"use client";

import { Chip, Switch, type Tone } from "@/components/ui";
import { CLOUD_META, type Cloud, type Controls, type Estate, type Finding } from "@/lib/api";

type Def = { key: keyof Controls; label: string; invert?: boolean; clouds: Cloud[]; hint: string };

const DEFS: Def[] = [
  { key: "publicBlocked", label: "Public access blocked", clouds: ["aws", "azure", "gcp"], hint: "Turn off to simulate someone disabling the safety net" },
  { key: "publicGrant", label: "Not shared publicly", invert: true, clouds: ["aws", "azure", "gcp"], hint: "Turn off to simulate a public read grant" },
  { key: "encrypted", label: "Encrypted at rest", clouds: ["aws"], hint: "Azure and Google Cloud always encrypt" },
  { key: "versioning", label: "Versioning on", clouds: ["aws", "azure", "gcp"], hint: "Protects against accidental or malicious deletes" },
  { key: "https", label: "HTTPS enforced", clouds: ["aws", "azure"], hint: "Not applicable on Google Cloud" },
];

const CLASS_TONE: Record<string, Tone> = { FERPA: "pink", PHI: "pink", PII: "lilac", FINANCIAL: "sun", PUBLIC: "mint", INTERNAL: "sky" };

export function EstatePanel({
  estate,
  findings,
  onToggle,
  disabled,
}: {
  estate: Estate;
  findings: Finding[];
  onToggle: (name: string, key: keyof Controls, value: boolean) => void;
  disabled: boolean;
}) {
  return (
    <ul className="space-y-4" aria-label="Simulated storage estate">
      {estate.resources.map((r) => {
        const issues = findings.filter((f) => f.resource.endsWith(r.name)).length;
        const dc = r.tags.DataClass;
        return (
          <li key={r.name} className={`card-flat p-4 transition-colors ${issues ? "bg-coral-100/60" : "bg-white"}`}>
            <div className="flex flex-wrap items-center gap-2">
              <Chip tone={CLOUD_META[r.cloud].tone}>{CLOUD_META[r.cloud].label}</Chip>
              {dc && <Chip tone={CLASS_TONE[dc] ?? "white"}>{dc}</Chip>}
              {r.tags.Environment && <Chip>{r.tags.Environment}</Chip>}
              <span
                className={`ml-auto rounded-full border-2 border-ink px-2.5 py-0.5 text-xs font-extrabold ${issues ? "bg-coral text-white" : "bg-mint"}`}
              >
                {issues ? `${issues} issue${issues > 1 ? "s" : ""}` : "healthy"}
              </span>
            </div>
            <p className="mt-2 break-all font-mono text-sm font-bold">{r.name}</p>
            {r.tags.Purpose && <p className="text-xs text-muted">purpose: {r.tags.Purpose}</p>}
            <div className="mt-2 grid gap-0.5 sm:grid-cols-2">
              {DEFS.filter((d) => d.clouds.includes(r.cloud)).map((d) => {
                const raw = !!r.controls[d.key];
                return (
                  <Switch
                    key={d.key}
                    label={d.label}
                    hint={d.hint}
                    checked={d.invert ? !raw : raw}
                    disabled={disabled}
                    onChange={(next) => onToggle(r.name, d.key, d.invert ? !next : next)}
                  />
                );
              })}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
