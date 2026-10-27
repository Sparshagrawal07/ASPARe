import { Database, Eye, Lock, ScrollText } from "lucide-react";
import type { Metadata } from "next";
import { Chip, SectionHeading } from "@/components/ui";

export const metadata: Metadata = {
  title: "Trust and safety",
  description: "How ASPARe keeps automatic remediation safe, what it stores, and exactly what has and has not been verified.",
};

const GUARANTEES = [
  ["Tag gate on every fix", "ASPARe only changes buckets tagged aspare-autofix=true, plus an optional allow-list. The fix role also carries a matching tag condition as a second lock."],
  ["Context can only lower, never raise", "Fusion can turn an automatic fix into an alert. It can never turn an alert into an automatic fix."],
  ["Verify, do not trust", "A fix counts only when ASPARe re-reads the bucket and the original rule no longer fires."],
  ["Order-aware fixes", "Policy edits run before the Public Access Block, because S3 refuses to save a public policy once it is blocked. Found on a real account."],
  ["Watching and fixing are separate", "Scanning uses a read-only role with no write permission. Fixing uses a different role you create only if you want it."],
  ["LLM is advisory", "Any AI explanation is advice only. It has no tools, never acts, and treats bucket names and tags as untrusted data."],
];

const STATUS: [string, string, string, "ok" | "warn"][] = [
  ["AWS S3 detect, fix and verify", "Real AWS account: live scans, tag-gated fixes, deployed pipeline", "", "ok"],
  ["Sign-in and one-click AWS connection", "Cross-account read-only role with external id, scanned a real account end to end", "Accounts beyond the project team's own", "warn"],
  ["Fixing on a real connected account", "Fix logic and the tag gate tested on simulated AWS and on a real account in the earlier showcase", "The tag condition inside the fix role on real buckets, and the hosted fix flow on real AWS", "warn"],
  ["Fusion and anomaly scoring", "Unit tests and a synthetic benchmark", "Real-world accuracy (labels are project-authored)", "warn"],
  ["Azure and Google Cloud", "Mapping and fixes tested against simulated APIs; demo above", "Real accounts: connections are on the waitlist", "warn"],
];

export default function TrustPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <span className="inline-block -rotate-1 rounded-full border-2 border-ink bg-lilac px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em]">Trust and safety</span>
      <h1 className="mt-4 text-5xl font-extrabold leading-[1.02] sm:text-6xl">Automatic fixes need automatic humility</h1>
      <p className="mt-4 max-w-2xl text-xl text-muted">A tool that can change your cloud has to earn trust. Here is what ASPARe guarantees, what it stores, and where we have not proven something yet.</p>

      <section className="mt-14" aria-labelledby="g">
        <SectionHeading kicker="Guarantees" title={<span id="g">How ASPARe stays safe</span>} tone="mint" />
        <ul className="mt-8 grid gap-5 sm:grid-cols-2">
          {GUARANTEES.map(([t, d], i) => (
            <li key={t} className={`card lift p-6 ${["bg-mint-100", "bg-sun-100", "bg-sky-100", "bg-peri-100", "bg-pink-100", "bg-lilac-100"][i]}`}>
              <h3 className="text-xl font-extrabold">{t}</h3>
              <p className="mt-2 text-[16px] leading-relaxed text-muted">{d}</p>
            </li>
          ))}
        </ul>
      </section>

      <section className="mt-20" aria-labelledby="data">
        <SectionHeading kicker="Your data" title={<span id="data">What we store, and what we never touch</span>} tone="sky" />
        <div className="mt-8 grid gap-5 md:grid-cols-3">
          <div className="card bg-white p-6"><Database aria-hidden="true" /><h3 className="mt-3 text-xl font-extrabold">Stored</h3><ul className="mt-2 list-disc space-y-1.5 pl-5 text-[15px] text-muted"><li>Your email, name and a salted password hash</li><li>Account id, role names and your private connection id</li><li>Bucket names, tags and finding results from your last five scans</li><li>An audit log of what ASPARe did</li></ul></div>
          <div className="card bg-white p-6"><Lock aria-hidden="true" /><h3 className="mt-3 text-xl font-extrabold">Never stored</h3><ul className="mt-2 list-disc space-y-1.5 pl-5 text-[15px] text-muted"><li>AWS access keys or secrets: none exist</li><li>The temporary credentials, which live one hour in memory</li><li>The contents of any object in any bucket</li></ul></div>
          <div className="card bg-white p-6"><Eye aria-hidden="true" /><h3 className="mt-3 text-xl font-extrabold">Yours to control</h3><ul className="mt-2 list-disc space-y-1.5 pl-5 text-[15px] text-muted"><li>Delete the stack: access ends at once</li><li>Disconnect: the account and its scans are erased</li><li>No analytics or tracking scripts load here</li></ul></div>
        </div>
      </section>

      <section className="mt-20" aria-labelledby="v">
        <SectionHeading kicker="Honest status" title={<span id="v">What is verified, and what is not</span>} sub="We would rather you hear the limits from us." tone="sun" />
        <div className="card-flat mt-8 overflow-x-auto bg-white">
          <table className="w-full min-w-[680px] text-left text-[15px]">
            <caption className="sr-only">Verification status of ASPARe capabilities</caption>
            <thead>
              <tr className="border-b-2 border-ink text-sm">
                <th scope="col" className="px-5 py-4">Capability</th>
                <th scope="col" className="px-5 py-4">Evidence</th>
                <th scope="col" className="px-5 py-4">Not yet verified</th>
              </tr>
            </thead>
            <tbody>
              {STATUS.map(([cap, ev, gap, tone]) => (
                <tr key={cap} className="border-b border-ink/15 last:border-0">
                  <th scope="row" className="px-5 py-4 font-bold">{cap} <Chip tone={tone === "ok" ? "mint" : "sun"} className="ml-1">{tone === "ok" ? "verified" : "partly verified"}</Chip></th>
                  <td className="px-5 py-4 text-muted">{ev}</td>
                  <td className="px-5 py-4 text-muted">{gap || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-16 grid gap-6 lg:grid-cols-2" aria-labelledby="b">
        <div className="card bg-peri-100 p-6">
          <ScrollText aria-hidden="true" />
          <h2 id="b" className="mt-3 text-2xl font-extrabold">About the benchmark</h2>
          <p className="mt-2 text-[16px] leading-relaxed text-muted">On 17 hand-labelled cases, fusing context and behaviour with the rules raised decision accuracy from 71% to 100% and removed every unsafe auto-fix. The labels were written by the project, not independent annotators, and the set is small. It is a regression check, not evidence of real-world accuracy.</p>
        </div>
        <div className="card bg-coral-100 p-6">
          <h2 className="text-2xl font-extrabold">Early access, honestly</h2>
          <p className="mt-2 text-[16px] leading-relaxed text-muted">ASPARe is free while in early access and runs on free infrastructure, so expect limits: five connected accounts each, daily automatic scans, and up to 200 buckets per scan.</p>
        </div>
      </section>
    </div>
  );
}
