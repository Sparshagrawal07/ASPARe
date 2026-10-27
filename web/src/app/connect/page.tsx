import { Eye, KeyRound, PlugZap, ShieldCheck, Trash2, Wrench } from "lucide-react";
import type { Metadata } from "next";
import { ButtonLink, Chip, SectionHeading } from "@/components/ui";

export const metadata: Metadata = {
  title: "How it connects",
  description: "ASPARe connects to your AWS account through a role you create and can delete. No keys are shared or stored.",
};

const READ = ["s3:ListAllMyBuckets", "s3:ListBucket", "s3:GetBucketLocation", "s3:GetBucketTagging", "s3:GetBucketAcl", "s3:GetBucketPolicy", "s3:GetBucketVersioning", "s3:GetEncryptionConfiguration", "s3:GetBucketPublicAccessBlock", "s3:GetBucketOwnershipControls"];
const WRITE = ["s3:PutBucketPublicAccessBlock", "s3:PutEncryptionConfiguration", "s3:PutBucketVersioning", "s3:PutBucketPolicy", "s3:PutBucketAcl"];

export default function ConnectPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <span className="inline-block -rotate-1 rounded-full border-2 border-ink bg-sky px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em]">How it connects</span>
      <h1 className="mt-4 text-5xl font-extrabold leading-[1.02] sm:text-6xl">One click in AWS. No keys, ever.</h1>
      <p className="mt-4 max-w-2xl text-xl text-muted">
        ASPARe uses the same pattern as the best cloud-security products: you create a role, we are allowed to borrow it for a
        few minutes at a time, and you can delete it whenever you like.
      </p>

      <ol className="mt-12 grid gap-6 md:grid-cols-3">
        {[
          { icon: PlugZap, t: "You press one button", d: "ASPARe opens a prefilled CloudFormation page in your console. You tick the box and press Create stack.", tone: "bg-sun" },
          { icon: KeyRound, t: "A role appears, locked to you", d: "The role trusts only ASPARe and only when it presents your private connection id, which stops anyone else borrowing it.", tone: "bg-sky" },
          { icon: Eye, t: "ASPARe notices on its own", d: "No pasting ARNs back. The dashboard checks for the role and starts the first scan the moment it works.", tone: "bg-mint" },
        ].map(({ icon: Icon, ...s }, i) => (
          <li key={s.t} className="card lift relative bg-white p-7 pt-10">
            <span className={`absolute -top-6 left-6 flex h-12 w-12 items-center justify-center rounded-full border-2 border-ink font-display text-2xl font-extrabold ${s.tone}`}>{i + 1}</span>
            <Icon size={30} aria-hidden="true" />
            <h2 className="mt-4 text-2xl font-extrabold">{s.t}</h2>
            <p className="mt-2 text-[16px] leading-relaxed text-muted">{s.d}</p>
          </li>
        ))}
      </ol>

      <section className="mt-20" aria-labelledby="perm">
        <SectionHeading kicker="Exactly what you grant" title={<span id="perm">Two roles, kept apart on purpose</span>} sub="Watching and fixing are different powers, so they live in different roles. The second one is optional." tone="lilac" />
        <div className="mt-10 grid gap-6 lg:grid-cols-2">
          <article className="card bg-mint-100 p-6">
            <div className="flex items-center gap-2"><ShieldCheck aria-hidden="true" /><h3 className="text-2xl font-extrabold">Read-only role</h3><Chip tone="mint" className="ml-auto">always</Chip></div>
            <p className="mt-2 text-[15px] text-muted">Reads bucket settings. Cannot read a single file, and cannot change anything.</p>
            <ul className="mt-4 flex flex-wrap gap-2">{READ.map((a) => <li key={a} className="rounded-lg border-2 border-ink bg-white px-2 py-1 font-mono text-xs">{a}</li>)}</ul>
            <a className="mt-5 inline-block text-sm font-extrabold text-peri underline underline-offset-4" href="/templates/aspare-access.yaml" target="_blank" rel="noreferrer">Read the template</a>
          </article>
          <article className="card bg-lilac-100 p-6">
            <div className="flex items-center gap-2"><Wrench aria-hidden="true" /><h3 className="text-2xl font-extrabold">Fix role</h3><Chip tone="lilac" className="ml-auto">optional</Chip></div>
            <p className="mt-2 text-[15px] text-muted">Changes five settings, and only on buckets you tag <code className="font-mono">aspare-autofix=true</code>. ASPARe checks the tag too, so there are two locks.</p>
            <ul className="mt-4 flex flex-wrap gap-2">{WRITE.map((a) => <li key={a} className="rounded-lg border-2 border-ink bg-white px-2 py-1 font-mono text-xs">{a}</li>)}</ul>
            <a className="mt-5 inline-block text-sm font-extrabold text-peri underline underline-offset-4" href="/templates/aspare-autofix.yaml" target="_blank" rel="noreferrer">Read the template</a>
          </article>
        </div>
      </section>

      <section className="mt-16" aria-labelledby="leave">
        <div className="card flex flex-col items-start gap-4 bg-coral-100 p-7 sm:flex-row sm:items-center">
          <Trash2 size={34} className="shrink-0" aria-hidden="true" />
          <div>
            <h2 id="leave" className="text-2xl font-extrabold">Leaving is one delete away</h2>
            <p className="mt-1 text-[16px] text-muted">Delete the stack in CloudFormation and access ends immediately. Disconnecting inside ASPARe also removes the account from your dashboard.</p>
          </div>
        </div>
        <div className="mt-8 flex flex-wrap gap-4">
          <ButtonLink href="/sign-up" tone="coral" className="px-8 py-4 text-lg">Start free</ButtonLink>
          <ButtonLink href="/demo" tone="white" className="px-8 py-4 text-lg">Try the demo first</ButtonLink>
        </div>
      </section>
    </div>
  );
}
