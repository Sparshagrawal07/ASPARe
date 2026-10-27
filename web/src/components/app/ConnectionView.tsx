"use client";

import { Check, RefreshCw, Trash2, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Chip } from "@/components/ui";
import { Diff } from "@/components/demo/Diff";
import { FindingCard } from "@/components/demo/FindingCard";
import { ago, appApi, type AccountScan, type Connection, type FixOutcome } from "@/lib/app-api";
import { ConnectedBadge, SetupPanel } from "./SetupPanel";
import { useRequireUser } from "./useRequireUser";

export function ConnectionView({ id }: { id: string }) {
  const user = useRequireUser();
  const router = useRouter();
  const params = useSearchParams();
  const [conn, setConn] = useState<Connection | null>(null);
  const [scan, setScan] = useState<AccountScan | null>(null);
  const [outcomes, setOutcomes] = useState<FixOutcome[]>([]);
  const [busy, setBusy] = useState<null | "scan" | "fix" | "save">(null);
  const [error, setError] = useState<string | null>(null);
  const [showFixSetup, setShowFixSetup] = useState(false);
  const autoScanned = useRef(false);

  useEffect(() => {
    if (!user) return;
    let alive = true;
    appApi
      .get(id)
      .then((r) => {
        if (!alive) return;
        setConn(r.connection);
        setScan(r.scan);
      })
      .catch((e) => alive && setError(e instanceof Error ? e.message : "Could not load this account"));
    return () => {
      alive = false;
    };
  }, [user, id]);

  const doScan = useCallback(async () => {
    setBusy("scan");
    setError(null);
    try {
      const r = await appApi.scan(id);
      setScan(r.scan);
      setConn(r.connection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Scan failed");
    } finally {
      setBusy(null);
    }
  }, [id]);

  useEffect(() => {
    if (conn?.status === "connected" && !scan && !autoScanned.current) {
      autoScanned.current = true;
      void doScan();
    }
  }, [conn, scan, doScan]);

  async function fix(ids: string[]) {
    setBusy("fix");
    setError(null);
    try {
      const r = await appApi.fix(id, ids);
      setOutcomes((p) => [...r.outcomes, ...p]);
      setScan(r.scan);
      setConn(r.connection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Fix failed");
    } finally {
      setBusy(null);
    }
  }

  async function save(patch: Parameters<typeof appApi.patch>[1]) {
    setBusy("save");
    setError(null);
    try {
      setConn((await appApi.patch(id, patch)).connection);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save");
    } finally {
      setBusy(null);
    }
  }

  if (user === undefined || (!conn && !error)) return <p className="px-5 py-20 text-center text-muted" role="status">Loading...</p>;
  if (!conn) {
    return (
      <div className="mx-auto max-w-xl px-5 py-20 text-center">
        <p role="alert" className="font-medium text-bad">{error}</p>
        <Link href="/app" className="mt-4 inline-block font-bold text-peri underline">Back to dashboard</Link>
      </div>
    );
  }

  const findings = scan?.result.findings ?? [];
  const autoIds = findings.filter((f) => f.decision === "AUTO_REMEDIATE" && f.autofixAllowed).map((f) => f.id);
  const working = busy !== null;
  const fixOn = conn.fixStatus === "connected";

  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <Link href="/app" className="text-sm font-bold text-peri underline underline-offset-4">All accounts</Link>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="text-5xl font-extrabold leading-tight">{conn.name}</h1>
        {conn.status === "connected" && <ConnectedBadge>Connected</ConnectedBadge>}
      </div>
      <p className="mt-1 font-mono text-sm text-muted">AWS {conn.accountId} / {conn.region} / last scan {ago(conn.lastScanAt)}</p>

      {error && <p role="alert" className="card-flat mt-5 bg-coral-100 px-4 py-3 text-sm font-medium text-bad">{error}</p>}

      {conn.status !== "connected" && (
        <div className="mt-8 max-w-2xl">
          <SetupPanel conn={conn} kind="access" onConnected={(c) => { setConn(c); setError(null); }} />
          {params.get("setup") && <p className="mt-3 text-sm text-muted">Nothing is scanned until this role exists.</p>}
        </div>
      )}

      {conn.status === "connected" && (
        <div className="mt-8 grid gap-8 lg:grid-cols-[minmax(0,7fr)_minmax(0,4fr)]">
          <section aria-labelledby="results">
            <div className="card-flat flex flex-wrap items-center gap-3 bg-sun-100 p-3">
              <h2 id="results" className="mr-auto text-2xl font-extrabold">Findings</h2>
              <Button tone="white" disabled={working} onClick={doScan}>
                <RefreshCw size={16} className={busy === "scan" ? "animate-spin" : ""} aria-hidden="true" />
                {busy === "scan" ? "Scanning..." : "Scan now"}
              </Button>
              <Button tone="mint" disabled={working || !fixOn || autoIds.length === 0} onClick={() => fix(autoIds)}>
                {busy === "fix" ? "Fixing..." : `Auto-fix ${autoIds.length} safe finding${autoIds.length === 1 ? "" : "s"}`}
              </Button>
            </div>
            {scan && (
              <dl className="mt-3 grid grid-cols-2 gap-2 text-center sm:grid-cols-4">
                {[["Buckets", scan.result.summary.buckets, "bg-sky-100"], ["Findings", scan.result.summary.total, "bg-white"], ["Auto-fixable", scan.result.summary.auto, "bg-mint-100"], ["Held for human", scan.result.summary.held, "bg-sun-100"]].map(([l, v, bg]) => (
                  <div key={l as string} className={`rounded-xl border-2 border-ink px-2 py-2 ${bg}`}>
                    <dd className="font-display text-3xl font-extrabold">{v}</dd>
                    <dt className="text-[11px] font-bold text-muted">{l}</dt>
                  </div>
                ))}
              </dl>
            )}
            {scan?.result.summary.truncated && <p className="mt-3 text-sm text-muted">This account has more than 200 buckets; the first 200 were scanned.</p>}
            {busy === "scan" && !scan && (
              <p className="mt-6 flex items-center gap-3 font-medium text-muted" role="status">
                <span className="h-5 w-5 animate-spin rounded-full border-4 border-ink border-t-sun" aria-hidden="true" /> Reading every bucket. Large accounts take a minute...
              </p>
            )}
            {!fixOn && findings.some((f) => f.canFix) && (
              <p className="card-flat mt-4 bg-lilac-100 px-4 py-3 text-sm">Fixes are off. Enable fix access on the right if you want ASPARe to repair findings on buckets you opt in.</p>
            )}

            {scan && scan.result.incidents.length > 0 && (
              <div className="mt-5 space-y-2">
                {scan.result.incidents.slice(0, 3).map((i) => (
                  <div key={i.id} className="card-flat bg-coral-100 px-4 py-3">
                    <p className="text-xs font-extrabold uppercase tracking-wider text-bad">Incident: {i.kind.replace(/-/g, " ")} <span className="ml-2 font-mono normal-case tracking-normal text-ink/80">{i.resource}</span></p>
                    <p className="mt-1 text-sm">{i.summary}</p>
                  </div>
                ))}
              </div>
            )}

            {outcomes.length > 0 && (
              <div className="mt-6">
                <h3 className="text-xl font-extrabold">Applied and verified</h3>
                <ul className="mt-3 space-y-3">
                  {outcomes.map((o) => (
                    <li key={`${o.findingId}-${o.action}`} className={`card-flat rise p-4 ${o.verified ? "bg-mint-100/60" : "bg-coral-100"}`}>
                      <p className="flex items-center gap-2 font-bold">
                        {o.verified ? <Check size={18} className="text-ok" aria-hidden="true" /> : <TriangleAlert size={18} className="text-bad" aria-hidden="true" />}
                        {o.verified ? "Verified" : "Not applied"}: <span className="font-mono text-peri">{o.resource}</span>
                      </p>
                      <p className="mt-1 text-xs text-muted">{o.action}. {o.message}</p>
                      {o.verified && (
                        <div className="mt-3 grid gap-2 text-xs sm:grid-cols-2">
                          <div className="rounded-xl border-2 border-ink bg-coral-100 p-2.5"><p className="mb-1 font-extrabold uppercase text-bad">Before</p><Diff lines={o.before} other={o.after} tone="before" /></div>
                          <div className="rounded-xl border-2 border-ink bg-mint-100 p-2.5"><p className="mb-1 font-extrabold uppercase text-ok">After</p><Diff lines={o.after} other={o.before} tone="after" /></div>
                        </div>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {scan && (
              <div className="mt-6 space-y-4">
                {findings.length === 0 ? (
                  <div className="card-flat bg-mint-100 p-8 text-center">
                    <p className="text-2xl font-extrabold">All {scan.result.summary.buckets} buckets look healthy.</p>
                    <p className="mt-1 text-sm text-muted">ASPARe re-checks daily and will flag any change.</p>
                  </div>
                ) : (
                  findings.map((f) => (
                    <FindingCard
                      key={f.id}
                      f={f}
                      busy={working}
                      fixable={fixOn && f.autofixAllowed}
                      fixHint={!fixOn ? "Enable fix access to repair this." : "Opt this bucket in by tagging it aspare-autofix=true (and adding it to the allow-list if you use one)."}
                      onFix={(fid) => fix([fid])}
                    />
                  ))
                )}
              </div>
            )}
          </section>

          <aside className="space-y-6" aria-label="Account settings">
            <div className="card bg-white p-5">
              <h3 className="text-xl font-extrabold">Fixing</h3>
              {fixOn ? (
                <>
                  <p className="mt-2 flex items-center gap-2 text-sm font-medium"><Chip tone="mint">Fix access on</Chip> separate tag-gated role</p>
                  <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm">
                    <input type="checkbox" className="mt-1 h-5 w-5 accent-peri" checked={conn.mode === "autofix"} disabled={working} onChange={(e) => save({ mode: e.target.checked ? "autofix" : "monitor" })} />
                    <span><b>Fix automatically after each daily scan.</b> Only findings ASPARe is confident about, on opted-in buckets.</span>
                  </label>
                </>
              ) : showFixSetup ? (
                <div className="mt-3"><SetupPanel conn={conn} kind="autofix" onConnected={(c) => { setConn(c); setShowFixSetup(false); }} /></div>
              ) : (
                <>
                  <p className="mt-2 text-sm text-muted">Currently watch-only. Fixes use a second role you create only if you want them, limited to buckets tagged <code className="font-mono">aspare-autofix=true</code>.</p>
                  <Button tone="lilac" className="mt-4" onClick={() => setShowFixSetup(true)}>Enable fix access</Button>
                </>
              )}
            </div>

            <div className="card bg-white p-5">
              <h3 className="text-xl font-extrabold">Buckets</h3>
              <p className="mt-1 text-xs text-muted">Optional allow-list. When any are selected, fixes touch only those.</p>
              <ul className="mt-3 max-h-80 space-y-1 overflow-y-auto pr-1">
                {(scan?.result.inventory ?? []).map((b) => (
                  <li key={b.name} className="flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-sun-100">
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-peri"
                      id={`b-${b.name}`}
                      checked={conn.allowedBuckets.includes(b.name)}
                      disabled={working}
                      onChange={(e) => save({ allowedBuckets: e.target.checked ? [...conn.allowedBuckets, b.name] : conn.allowedBuckets.filter((x) => x !== b.name) })}
                    />
                    <label htmlFor={`b-${b.name}`} className="min-w-0 flex-1 cursor-pointer truncate font-mono text-xs" title={b.name}>{b.name}</label>
                    {b.autofixOptIn && <Chip tone="mint">opted in</Chip>}
                    {!b.readable && <Chip tone="coral">unreadable</Chip>}
                    <span className={`w-6 text-right text-xs font-bold ${b.findings ? "text-bad" : "text-ok"}`}>{b.findings || "ok"}</span>
                  </li>
                ))}
                {!scan && <li className="text-sm text-muted">Scan to list your buckets.</li>}
              </ul>
            </div>

            <div className="card-flat bg-coral-100 p-5">
              <h3 className="text-lg font-extrabold">Disconnect</h3>
              <p className="mt-1 text-sm text-muted">Removes this account from ASPARe. To end AWS-side access too, delete the <code className="font-mono">ASPARe-Access</code>{fixOn ? " and ASPARe-AutoFix" : ""} stack{fixOn ? "s" : ""} in CloudFormation.</p>
              <Button tone="white" className="mt-3 !text-bad" disabled={working} onClick={async () => { if (confirm("Disconnect this account from ASPARe?")) { await appApi.remove(id); router.push("/app"); } }}>
                <Trash2 size={16} aria-hidden="true" /> Disconnect
              </Button>
            </div>
          </aside>
        </div>
      )}
    </div>
  );
}
