"use client";

import { Cloud, Plus, ShieldCheck, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { authClient } from "@/lib/auth-client";
import { ago, appApi, type Connection } from "@/lib/app-api";
import { Button, ButtonLink, Chip } from "@/components/ui";
import { useRequireUser } from "./useRequireUser";

function WaitlistCard({ provider, label, tone }: { provider: "azure" | "gcp"; label: string; tone: string }) {
  const [state, setState] = useState<"idle" | "busy" | "done" | "error">("idle");
  return (
    <div className={`card-flat p-5 ${tone}`}>
      <div className="flex items-center gap-2">
        <Cloud size={20} aria-hidden="true" />
        <h3 className="text-lg font-extrabold">{label}</h3>
        <Chip className="ml-auto">Coming soon</Chip>
      </div>
      <p className="mt-2 text-sm text-muted">Scanning and fixing run in the demo today. Join the list and we will tell you the day account connections open.</p>
      <Button
        tone="white"
        className="mt-4 !px-4 !py-2 !text-sm"
        disabled={state === "busy" || state === "done"}
        onClick={async () => {
          setState("busy");
          try {
            await appApi.waitlist(provider);
            setState("done");
          } catch {
            setState("error");
          }
        }}
      >
        {state === "done" ? "You are on the list" : state === "busy" ? "Adding..." : state === "error" ? "Try again" : "Join the waitlist"}
      </Button>
    </div>
  );
}

export function Overview() {
  const user = useRequireUser();
  const [items, setItems] = useState<Connection[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    appApi.list().then((r) => setItems(r.connections)).catch((e) => setError(e.message));
  }, [user]);

  if (user === undefined) return <p className="px-5 py-20 text-center font-medium text-muted" role="status">Loading your workspace...</p>;

  const totalFindings = (items ?? []).reduce((n, c) => n + (c.lastSummary?.total ?? 0), 0);
  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="inline-block -rotate-1 rounded-full border-2 border-ink bg-mint px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em]">Dashboard</span>
          <h1 className="mt-3 text-5xl font-extrabold leading-tight">Hi {user.name.split(" ")[0]}.</h1>
          <p className="mt-2 text-lg text-muted">{items?.length ? `${totalFindings} open finding${totalFindings === 1 ? "" : "s"} across ${items.length} account${items.length > 1 ? "s" : ""}.` : "Connect your first cloud account to get started."}</p>
        </div>
        <div className="flex gap-3">
          <ButtonLink href="/app/connect" tone="coral"><Plus size={18} aria-hidden="true" /> Connect AWS</ButtonLink>
          <Button tone="white" onClick={async () => {
              await authClient.signOut();
              // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full reload on purpose: wipes client state
              window.location.assign("/");
            }}>Sign out</Button>
        </div>
      </div>

      {error && <p role="alert" className="card-flat mt-6 bg-coral-100 px-4 py-3 text-sm font-medium text-bad">{error}</p>}

      <section className="mt-10" aria-labelledby="accounts">
        <h2 id="accounts" className="text-2xl font-extrabold">Your accounts</h2>
        {items === null ? (
          <p className="mt-4 text-muted" role="status">Loading...</p>
        ) : items.length === 0 ? (
          <div className="card mt-4 bg-sun-100 p-10 text-center">
            <ShieldCheck className="mx-auto" size={44} aria-hidden="true" />
            <h3 className="mt-3 text-3xl font-extrabold">Nothing connected yet</h3>
            <p className="mx-auto mt-2 max-w-md text-lg text-muted">It takes about two minutes and one click in your AWS console. We never see or store a key.</p>
            <ButtonLink href="/app/connect" tone="coral" className="mt-6 px-8 py-4 text-lg"><Plus size={20} aria-hidden="true" /> Connect AWS</ButtonLink>
          </div>
        ) : (
          <ul className="mt-4 grid gap-5 md:grid-cols-2">
            {items.map((c) => (
              <li key={c.id}>
                <Link href={`/app/c/${c.id}`} className="card lift block bg-white p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <Chip tone="sun">AWS</Chip>
                    <Chip tone={c.status === "connected" ? "mint" : c.status === "error" ? "coral" : "sky"}>
                      {c.status === "connected" ? "Connected" : c.status === "error" ? "Needs attention" : "Finish setup"}
                    </Chip>
                    {c.fixStatus === "connected" && <Chip tone="lilac">Fixes enabled</Chip>}
                  </div>
                  <h3 className="mt-3 text-2xl font-extrabold">{c.name}</h3>
                  <p className="font-mono text-sm text-muted">{c.accountId} / {c.region}</p>
                  {c.lastSummary ? (
                    <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                      {[["Buckets", c.lastSummary.buckets, "bg-sky-100"], ["Findings", c.lastSummary.total, c.lastSummary.total ? "bg-coral-100" : "bg-mint-100"], ["Auto-fixable", c.lastSummary.auto, "bg-mint-100"]].map(([l, v, bg]) => (
                        <div key={l as string} className={`rounded-xl border-2 border-ink py-2 ${bg}`}>
                          <p className="font-display text-2xl font-extrabold">{v}</p>
                          <p className="text-[11px] font-bold text-muted">{l}</p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="mt-4 flex items-center gap-2 text-sm text-muted"><TriangleAlert size={16} aria-hidden="true" /> {c.status === "connected" ? "Not scanned yet" : "Waiting for the AWS stack"}</p>
                  )}
                  <p className="mt-3 text-xs text-muted">Last scan: {ago(c.lastScanAt)}</p>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-12" aria-labelledby="more">
        <h2 id="more" className="text-2xl font-extrabold">More clouds</h2>
        <div className="mt-4 grid gap-5 md:grid-cols-2">
          <WaitlistCard provider="azure" label="Azure Blob Storage" tone="bg-sky-100" />
          <WaitlistCard provider="gcp" label="Google Cloud Storage" tone="bg-mint-100" />
        </div>
      </section>
      <section className="mt-16 border-t-2 border-ink/15 pt-6" aria-label="Account">
        <p className="text-sm text-muted">
          Want out? Deleting your account erases your connections, scan history and audit log from ASPARe. It does not touch AWS: delete the ASPARe stacks there too.
        </p>
        <Button
          tone="white"
          className="mt-3 !text-bad"
          onClick={async () => {
            if (!confirm("Delete your ASPARe account and all of its data? This cannot be undone.")) return;
            await fetch("/api/me", { method: "DELETE" });
            await authClient.signOut().catch(() => undefined);
            // eslint-disable-next-line @next/next/no-location-assign-relative-destination -- full reload on purpose: wipes client state
            window.location.assign("/");
          }}
        >
          Delete my account
        </Button>
      </section>
    </div>
  );
}
