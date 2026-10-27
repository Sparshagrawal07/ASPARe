"use client";

import { ChevronDown, Wrench } from "lucide-react";
import { Button, Chip, type Tone } from "@/components/ui";
import { CLOUD_META, type Decision, type Finding } from "@/lib/api";

const SEV: Record<Finding["severity"], Tone> = { CRITICAL: "coral", HIGH: "sun", MEDIUM: "sky", LOW: "white" as Tone };

const DECISION: Record<Decision, { label: string; tone: Tone }> = {
  AUTO_REMEDIATE: { label: "Auto-fix", tone: "mint" },
  ALERT_AND_LOG: { label: "Held for a human", tone: "sun" },
  MANUAL_REVIEW: { label: "Manual review", tone: "sun" },
  LOG_ONLY: { label: "Logged only", tone: "white" as Tone },
};

export function FindingCard({
  f,
  busy,
  onFix,
  fixable = true,
  fixHint,
}: {
  f: Finding;
  busy: boolean;
  onFix: (id: string) => void;
  fixable?: boolean;
  fixHint?: string;
}) {
  const decision = f.decision ? DECISION[f.decision] : null;
  const downgraded = f.ruleOnlyDecision === "AUTO_REMEDIATE" && f.decision !== "AUTO_REMEDIATE";
  const conf = Math.round((f.confidence ?? 0) * 100);
  const signals = f.anomaly.signals ?? [];
  const auto = f.decision === "AUTO_REMEDIATE";
  return (
    <article className="card-flat rise bg-white p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Chip tone={SEV[f.severity]}>{f.severity}</Chip>
        {decision && <Chip tone={decision.tone}>{decision.label}</Chip>}
        <Chip tone={CLOUD_META[f.cloud].tone}>{CLOUD_META[f.cloud].label}</Chip>
        {f.escalate && <Chip tone="coral">Escalate now</Chip>}
        <span className="ml-auto font-mono text-xs text-muted">priority {Math.round(f.priority ?? 0)}</span>
      </div>
      <h3 className="mt-2 text-xl font-extrabold">{f.title}</h3>
      <p className="break-all font-mono text-sm font-bold text-peri">{f.resource}</p>

      {downgraded && (
        <p className="mt-2 rounded-xl border-2 border-ink bg-sun-100 px-3 py-2 text-sm font-medium">
          A severity-only tool would auto-fix this. ASPARe holds it because context says the exposure may be intended.
        </p>
      )}

      <div className="mt-3 flex items-center gap-3">
        <div className="h-3 flex-1 overflow-hidden rounded-full border-2 border-ink bg-white" role="img" aria-label={`Confidence ${conf} percent`}>
          <div className="h-full bg-peri transition-all duration-700" style={{ width: `${conf}%` }} />
        </div>
        <span className="w-28 text-right text-xs font-bold text-muted">confidence {conf}%</span>
      </div>

      <details className="group mt-3">
        <summary className="flex cursor-pointer select-none list-none items-center gap-1 text-sm font-extrabold text-peri hover:text-ink">
          Why did ASPARe decide this?
          <ChevronDown size={16} className="transition-transform group-open:rotate-180" aria-hidden="true" />
        </summary>
        <div className="mt-3 space-y-3 text-sm leading-relaxed text-muted">
          <p><b className="text-ink">What is wrong. </b>{f.what}</p>
          <p><b className="text-ink">Why it matters. </b>{f.affects}</p>
          <div>
            <b className="text-ink">Decision trail</b>
            <ul className="mt-1 list-disc space-y-1 pl-5">
              {f.reasons.map((r) => <li key={r}>{r}</li>)}
            </ul>
          </div>
          {signals.length > 0 && (
            <div>
              <b className="text-ink">Behavioural signals</b>
              <ul className="mt-1 space-y-1">
                {signals.map((s) => (
                  <li key={s.name} className="flex gap-2">
                    <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full border border-ink bg-coral" aria-hidden="true" />
                    <span>{s.explanation}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p><b className="text-ink">Recommended action. </b>{f.analysis.recommendation}</p>
          {f.standards.length > 0 && <p className="text-xs">Maps to: {f.standards.join(" / ")}</p>}
        </div>
      </details>

      {f.canFix && f.decision !== "LOG_ONLY" && !fixable && fixHint && (
        <p className="mt-4 rounded-xl border-2 border-dashed border-ink/40 px-3 py-2 text-sm text-muted">{fixHint}</p>
      )}
      {f.canFix && f.decision !== "LOG_ONLY" && fixable && (
        <div className="mt-4">
          <Button tone={auto ? "mint" : "sun"} disabled={busy} onClick={() => onFix(f.id)}>
            <Wrench size={16} aria-hidden="true" />
            {auto ? "Fix now" : "I approve: fix it anyway"}
          </Button>
        </div>
      )}
    </article>
  );
}
