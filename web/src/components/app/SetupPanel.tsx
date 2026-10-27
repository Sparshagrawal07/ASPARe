"use client";

import { CheckCircle2, ExternalLink, Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { appApi, type Connection } from "@/lib/app-api";
import { Button } from "@/components/ui";

const POLL_MS = 4000;
const GIVE_UP_MS = 15 * 60 * 1000;

/** Opens the prefilled AWS stack and polls until the role exists, so the user never pastes anything back. */
export function SetupPanel({
  conn,
  kind,
  onConnected,
}: {
  conn: Connection;
  kind: "access" | "autofix";
  onConnected: (c: Connection) => void;
}) {
  const [phase, setPhase] = useState<"idle" | "launching" | "waiting" | "timeout">("idle");
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const started = useRef(0);

  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  async function check(): Promise<boolean> {
    try {
      const r = await appApi.verify(conn.id, kind);
      if (r.ok) {
        if (timer.current) clearInterval(timer.current);
        onConnected(r.connection);
        return true;
      }
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Check failed");
    }
    return false;
  }

  async function launch() {
    setError(null);
    setPhase("launching");
    try {
      const { url } = await appApi.launch(conn.id, kind);
      window.open(url, "_blank", "noopener");
      started.current = Date.now();
      setPhase("waiting");
      setSeconds(0);
      timer.current = setInterval(async () => {
        const elapsed = Date.now() - started.current;
        setSeconds(Math.round(elapsed / 1000));
        if (elapsed > GIVE_UP_MS) {
          if (timer.current) clearInterval(timer.current);
          setPhase("timeout");
          return;
        }
        await check();
      }, POLL_MS);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open AWS");
      setPhase("idle");
    }
  }

  const label = kind === "access" ? "read-only access" : "fix access";
  return (
    <div className="card bg-sun-100 p-6">
      <h3 className="text-2xl font-extrabold">{kind === "access" ? "Step 2 of 2: create the role in AWS" : "Enable fix access"}</h3>
      <ol className="mt-4 list-decimal space-y-2 pl-5 text-[16px]">
        <li>Press the button. AWS opens a page with everything prefilled.</li>
        <li>Tick the box that says it may create an IAM role, then press <b>Create stack</b>.</li>
        <li>Come back here. This page notices by itself, usually within a minute.</li>
      </ol>
      <div className="mt-5 flex flex-wrap items-center gap-3">
        <Button tone="coral" disabled={phase === "launching"} onClick={launch}>
          {phase === "launching" ? <Loader2 className="animate-spin" size={18} aria-hidden="true" /> : <ExternalLink size={18} aria-hidden="true" />}
          {phase === "waiting" || phase === "timeout" ? "Open AWS again" : `Open AWS and create ${label}`}
        </Button>
        {(phase === "waiting" || phase === "timeout") && (
          <Button tone="white" onClick={() => void check()}>Check now</Button>
        )}
      </div>
      {phase === "waiting" && (
        <p className="mt-4 flex items-center gap-2 font-medium" role="status">
          <Loader2 className="animate-spin" size={18} aria-hidden="true" /> Waiting for AWS to finish creating the role ({seconds}s)...
        </p>
      )}
      {phase === "timeout" && <p className="mt-4 font-medium text-bad" role="alert">Still not seeing the role. Check that the stack shows CREATE_COMPLETE in AWS, then press Check now.</p>}
      {error && <p className="mt-4 rounded-xl border-2 border-ink bg-white px-3 py-2 text-sm text-bad" role="alert">{error}</p>}
      <details className="mt-5 text-sm">
        <summary className="cursor-pointer font-extrabold text-peri">What exactly will this create?</summary>
        <p className="mt-2 text-muted">
          One IAM role named <code className="font-mono">{kind === "access" ? "ASPAReAccess" : "ASPAReFix"}-{conn.id.replace(/-/g, "").slice(0, 8)}</code>
          {kind === "access" ? ", allowed to read bucket settings (never objects) and nothing else." : ", allowed to change five security settings, only on buckets tagged aspare-autofix=true."}{" "}
          Only ASPARe, presenting your private connection id, can use it. Read the template yourself:{" "}
          <a className="font-bold text-peri underline" href={`/templates/${kind === "access" ? "aspare-access" : "aspare-autofix"}.yaml`} target="_blank" rel="noreferrer">view the CloudFormation template</a>.
        </p>
      </details>
    </div>
  );
}

export function ConnectedBadge({ children }: { children: React.ReactNode }) {
  return (
    <p className="inline-flex items-center gap-2 rounded-full border-2 border-ink bg-mint px-3 py-1 text-sm font-extrabold">
      <CheckCircle2 size={16} aria-hidden="true" /> {children}
    </p>
  );
}
