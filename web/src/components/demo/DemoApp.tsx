"use client";

import { Check, PartyPopper, RefreshCw, TriangleAlert, Wand2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui";
import { Diff } from "./Diff";
import { EstatePanel } from "./EstatePanel";
import { FindingCard } from "./FindingCard";
import { api, type Controls, type Estate, type Finding, type Outcome, type RemediateResult, type ScanResult } from "@/lib/api";

type Busy = null | "load" | "scan" | "fix";

const SECURE: Controls = { publicBlocked: true, encrypted: true, versioning: true, https: true, publicGrant: false };
const BROKEN: Controls = { publicBlocked: false, encrypted: false, versioning: false, https: false, publicGrant: true };
const KIND_ORDER = ["actor-campaign", "public-exposure-chain", "compound-misconfiguration"];

function withControls(estate: Estate, base: Controls): Estate {
  return {
    changes: [],
    resources: estate.resources.map((r) => ({
      ...r,
      controls: { ...base, encrypted: r.cloud === "aws" ? base.encrypted : true, https: r.cloud === "gcp" ? null : base.https },
    })),
  };
}

function Incident({ i }: { i: ScanResult["incidents"][number] }) {
  return (
    <div className="card-flat bg-coral-100 px-4 py-3">
      <p className="text-xs font-extrabold uppercase tracking-wider text-bad">
        Incident: {i.kind.replace(/-/g, " ")}
        {i.resource !== "*" && <span className="ml-2 font-mono normal-case tracking-normal text-ink/80">{i.resource}</span>}
      </p>
      <p className="mt-1 text-sm">{i.summary}</p>
    </div>
  );
}

function Incidents({ incidents }: { incidents: ScanResult["incidents"] }) {
  const sorted = [...incidents].sort((a, b) => KIND_ORDER.indexOf(a.kind) - KIND_ORDER.indexOf(b.kind));
  const rest = sorted.slice(2);
  return (
    <div className="mt-5 space-y-2">
      {sorted.slice(0, 2).map((i) => <Incident key={i.id} i={i} />)}
      {rest.length > 0 && (
        <details className="card-flat bg-white px-4 py-2">
          <summary className="cursor-pointer text-sm font-extrabold text-peri">{rest.length} more related incident{rest.length > 1 ? "s" : ""}</summary>
          <div className="mt-2 space-y-2 pb-2">{rest.map((i) => <Incident key={i.id} i={i} />)}</div>
        </details>
      )}
    </div>
  );
}

export function DemoApp() {
  const [base, setBase] = useState<Estate | null>(null);
  const [estate, setEstate] = useState<Estate | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [outcomes, setOutcomes] = useState<Outcome[]>([]);
  const [audit, setAudit] = useState<RemediateResult["audit"]>([]);
  const [busy, setBusy] = useState<Busy>("load");
  const [error, setError] = useState<string | null>(null);
  const [stale, setStale] = useState(false);

  const runScan = useCallback(async (e: Estate) => {
    setBusy("scan");
    setError(null);
    try {
      setScan(await api.scan(e));
      setStale(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed");
    } finally {
      setBusy(null);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const e = await api.estate();
        if (!alive) return;
        setBase(e);
        setEstate(e);
        await runScan(e);
      } catch (err) {
        if (alive) {
          setError(err instanceof Error ? err.message : "Could not load the demo");
          setBusy(null);
        }
      }
    })();
    return () => {
      alive = false;
    };
  }, [runScan]);

  function load(next: Estate) {
    setEstate(next);
    setOutcomes([]);
    setAudit([]);
    setScan(null);
    void runScan(next);
  }

  function toggle(name: string, key: keyof Controls, value: boolean) {
    if (!estate) return;
    setEstate({
      ...estate,
      resources: estate.resources.map((r) => (r.name === name ? { ...r, controls: { ...r.controls, [key]: value } } : r)),
    });
    setStale(true);
  }

  async function fix(ids: string[]) {
    if (!estate || ids.length === 0) return;
    setBusy("fix");
    setError(null);
    try {
      const res = await api.remediate(estate, ids);
      setEstate(res.estate);
      setOutcomes((prev) => [...res.outcomes, ...prev]);
      setAudit((prev) => [...prev, ...res.audit]);
      setScan(await api.scan(res.estate));
      setStale(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Fix failed");
    } finally {
      setBusy(null);
    }
  }

  const findings: Finding[] = scan?.findings ?? [];
  const autoIds = findings.filter((f) => f.decision === "AUTO_REMEDIATE" && f.canFix).map((f) => f.id);
  const working = busy !== null;

  if (busy === "load" && !estate) {
    return (
      <div className="card-flat mx-auto mt-10 flex max-w-md flex-col items-center gap-4 bg-white p-10 text-center" role="status">
        <span className="h-9 w-9 animate-spin rounded-full border-4 border-ink border-t-sun" aria-hidden="true" />
        <p className="font-medium text-muted">Starting the ASPARe engine...</p>
      </div>
    );
  }
  if (!estate) {
    return (
      <div className="card-flat mx-auto mt-10 max-w-lg bg-white p-8 text-center" role="alert">
        <TriangleAlert className="mx-auto text-bad" size={32} aria-hidden="true" />
        <h2 className="mt-2 text-2xl font-extrabold">The demo could not start</h2>
        <p className="mt-2 text-muted">{error}</p>
        <Button className="mt-5" onClick={() => location.reload()}>Try again</Button>
      </div>
    );
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
      <section aria-labelledby="estate-h">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="estate-h" className="text-2xl font-extrabold">1. Your simulated estate</h2>
          <div className="flex flex-wrap gap-2">
            {base && <Button tone="white" className="!px-3 !py-1.5 !text-xs" disabled={working} onClick={() => load(base)}>Campus story</Button>}
            <Button tone="white" className="!px-3 !py-1.5 !text-xs" disabled={working} onClick={() => load(withControls(estate, SECURE))}>All secure</Button>
            <Button tone="white" className="!px-3 !py-1.5 !text-xs" disabled={working} onClick={() => load(withControls(estate, BROKEN))}>Mayhem</Button>
          </div>
        </div>
        <p className="mt-2 text-sm text-muted">
          Flip any switch to misconfigure a bucket, then scan. This simulates AWS, Azure and Google Cloud running the real ASPARe
          engine. Nothing here touches a real account.
        </p>
        <div className="mt-4"><EstatePanel estate={estate} findings={findings} onToggle={toggle} disabled={working} /></div>
      </section>

      <section aria-labelledby="results-h" aria-live="polite">
        <div className="card-flat sticky top-[84px] z-10 bg-sun-100 p-3">
          <div className="flex flex-wrap items-center gap-3">
            <h2 id="results-h" className="mr-auto text-2xl font-extrabold">2. What ASPARe does</h2>
            <Button tone={stale ? "peri" : "white"} disabled={working} onClick={() => runScan(estate)}>
              <RefreshCw size={16} className={busy === "scan" ? "animate-spin" : ""} aria-hidden="true" />
              {busy === "scan" ? "Scanning..." : stale ? "Scan changes" : "Scan again"}
            </Button>
            <Button tone="mint" disabled={working || autoIds.length === 0} onClick={() => fix(autoIds)}>
              <Wand2 size={16} aria-hidden="true" />
              {busy === "fix" ? "Fixing..." : `Auto-fix ${autoIds.length} safe finding${autoIds.length === 1 ? "" : "s"}`}
            </Button>
          </div>
          {scan && (
            <dl className="mt-3 grid grid-cols-4 gap-2 text-center">
              {[
                ["Findings", scan.summary.total, "bg-white"],
                ["Auto-fixable", scan.summary.auto, "bg-mint-100"],
                ["Held for human", scan.summary.held, "bg-sun"],
                ["Escalations", scan.summary.escalations, "bg-coral-100"],
              ].map(([l, v, c]) => (
                <div key={l as string} className={`rounded-xl border-2 border-ink px-2 py-2 ${c}`}>
                  <dd className="font-display text-3xl font-extrabold">{v}</dd>
                  <dt className="text-[11px] font-bold text-muted">{l}</dt>
                </div>
              ))}
            </dl>
          )}
        </div>

        {error && <p role="alert" className="card-flat mt-4 bg-coral-100 px-4 py-3 text-sm font-medium text-bad">{error}</p>}
        {stale && !working && (
          <p className="card-flat mt-4 bg-sky-100 px-4 py-3 text-sm font-medium">You changed the estate. Press <b>Scan changes</b> to see what ASPARe makes of it.</p>
        )}
        {busy === "scan" && !scan && (
          <div className="mt-6 flex items-center gap-3 font-medium text-muted" role="status">
            <span className="h-5 w-5 animate-spin rounded-full border-4 border-ink border-t-sun" aria-hidden="true" />
            Reading every bucket and weighing the evidence...
          </div>
        )}

        {scan && scan.incidents.length > 0 && <Incidents incidents={scan.incidents} />}

        {outcomes.length > 0 && (
          <div className="mt-6">
            <h3 className="text-xl font-extrabold">Fixed and verified by re-reading the cloud</h3>
            <ul className="mt-3 space-y-3">
              {outcomes.map((o) => (
                <li key={`${o.findingId}-${o.action}`} className="card-flat rise bg-mint-100/60 p-4">
                  <div className="flex items-center gap-2">
                    <span className={`pop flex h-8 w-8 items-center justify-center rounded-full border-2 border-ink ${o.verified ? "bg-mint" : "bg-coral"}`} aria-hidden="true">
                      {o.verified ? <Check size={18} strokeWidth={3} /> : <TriangleAlert size={16} />}
                    </span>
                    <p className="font-bold">
                      {o.verified ? "Verified" : "Not verified"}: <span className="font-mono text-peri">{o.resource}</span>
                    </p>
                  </div>
                  <p className="mt-1 text-xs text-muted">action {o.action}. {o.message}</p>
                  <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                    <div className="rounded-xl border-2 border-ink bg-coral-100 p-2.5">
                      <p className="mb-1 font-extrabold uppercase tracking-wider text-bad">Before</p>
                      <Diff lines={o.before} other={o.after} tone="before" />
                    </div>
                    <div className="rounded-xl border-2 border-ink bg-mint-100 p-2.5">
                      <p className="mb-1 font-extrabold uppercase tracking-wider text-ok">After</p>
                      <Diff lines={o.after} other={o.before} tone="after" />
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        {scan && (
          <div className="mt-6">
            <h3 className="text-xl font-extrabold">Findings, most urgent first</h3>
            {findings.length === 0 ? (
              <div className="card-flat mt-3 bg-mint-100 p-8 text-center">
                <PartyPopper className="pop mx-auto text-ok" size={40} aria-hidden="true" />
                <p className="mt-2 text-xl font-extrabold">Everything is healthy</p>
                <p className="mt-1 text-sm text-muted">Now flip a switch on the left and scan to see ASPARe react.</p>
              </div>
            ) : (
              <div className="mt-3 space-y-4">
                {findings.map((f) => <FindingCard key={f.id} f={f} busy={working} onFix={(id) => fix([id])} />)}
              </div>
            )}
          </div>
        )}

        {audit.length > 0 && (
          <details className="card-flat mt-6 bg-white p-4">
            <summary className="cursor-pointer text-sm font-extrabold text-peri">Audit trail ({audit.length} records)</summary>
            <ul className="mt-3 space-y-1 font-mono text-xs text-muted">
              {audit.map((a, i) => <li key={i}>{a.action} / {a.result} / {a.resource} {a.rule ? `/ ${a.rule}` : ""}</li>)}
            </ul>
          </details>
        )}
      </section>
    </div>
  );
}
