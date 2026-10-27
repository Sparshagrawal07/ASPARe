"use client";

import { ArrowRight, Info } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { appApi } from "@/lib/app-api";
import { useRequireUser } from "./useRequireUser";

const REGIONS = ["us-east-1", "us-east-2", "us-west-2", "eu-west-1", "eu-central-1", "ap-south-1", "ap-southeast-1", "ap-southeast-2"];

export function ConnectWizard() {
  const user = useRequireUser();
  const router = useRouter();
  const [accountId, setAccountId] = useState("");
  const [name, setName] = useState("");
  const [region, setRegion] = useState("us-east-1");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user === undefined) return <p className="px-5 py-20 text-center text-muted" role="status">Loading...</p>;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const { connection } = await appApi.create({ provider: "aws", accountId: accountId.trim(), name: name.trim() || "My AWS account", region });
      router.push(`/app/c/${connection.id}?setup=1`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the connection");
      setBusy(false);
    }
  }

  const input = "mt-1.5 w-full rounded-xl border-2 border-ink bg-white px-4 py-3 text-[16px] font-normal focus:border-peri focus:outline-none";
  return (
    <div className="mx-auto max-w-2xl px-5 py-12">
      <Link href="/app" className="text-sm font-bold text-peri underline underline-offset-4">Back to dashboard</Link>
      <h1 className="mt-4 text-5xl font-extrabold leading-tight">Connect AWS</h1>
      <p className="mt-3 text-lg text-muted">Step 1 of 2. Tell us which account to watch. Next, AWS opens a prefilled page and you press Create.</p>

      <form onSubmit={submit} className="card mt-8 space-y-5 bg-white p-7" noValidate>
        <label className="block text-sm font-bold">
          AWS account id
          <input className={`${input} font-mono`} inputMode="numeric" placeholder="123456789012" value={accountId} onChange={(e) => setAccountId(e.target.value.replace(/\D/g, "").slice(0, 12))} required aria-describedby="acct-hint" />
          <span id="acct-hint" className="mt-1 block text-xs font-normal text-muted">12 digits, shown top-right in the AWS console under your name.</span>
        </label>
        <label className="block text-sm font-bold">
          Nickname
          <input className={input} placeholder="Production" value={name} maxLength={40} onChange={(e) => setName(e.target.value)} />
        </label>
        <label className="block text-sm font-bold">
          Region to open the console in
          <select className={input} value={region} onChange={(e) => setRegion(e.target.value)}>
            {REGIONS.map((r) => <option key={r}>{r}</option>)}
          </select>
          <span className="mt-1 block text-xs font-normal text-muted">Only affects where the setup page opens. Buckets in every region are scanned.</span>
        </label>
        <div className="flex gap-3 rounded-xl border-2 border-ink bg-sky-100 p-4 text-sm">
          <Info size={20} className="mt-0.5 shrink-0" aria-hidden="true" />
          <p>You will create a <b>read-only</b> role. It can see bucket settings, never your files, and cannot change anything. Deleting its stack ends access instantly.</p>
        </div>
        {error && <p role="alert" className="rounded-xl border-2 border-ink bg-coral-100 px-4 py-3 text-sm font-medium text-bad">{error}</p>}
        <button type="submit" disabled={busy || accountId.length !== 12} className="btn w-full bg-coral px-6 py-3.5 text-lg text-white">
          {busy ? "Creating..." : "Continue"} {!busy && <ArrowRight size={20} aria-hidden="true" />}
        </button>
      </form>
    </div>
  );
}
