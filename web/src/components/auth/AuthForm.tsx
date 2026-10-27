"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Mascot } from "@/components/Logo";
import { authClient } from "@/lib/auth-client";

type Mode = "sign-in" | "sign-up";

export function AuthForm({ mode }: { mode: Mode }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [social, setSocial] = useState<{ github: boolean; google: boolean }>({ github: false, google: false });
  const signUp = mode === "sign-up";

  useEffect(() => {
    fetch("/api/config", { cache: "no-store" })
      .then((r) => r.json())
      .then((c) => setSocial(c.social))
      .catch(() => undefined);
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const res = signUp
      ? await authClient.signUp.email({ email, password, name: name || email.split("@")[0] })
      : await authClient.signIn.email({ email, password });
    setBusy(false);
    if (res.error) {
      setError(res.error.message ?? "Something went wrong. Please try again.");
      return;
    }
    router.push("/app");
    router.refresh();
  }

  async function oauth(provider: "github" | "google") {
    setBusy(true);
    await authClient.signIn.social({ provider, callbackURL: "/app" });
  }

  const input = "w-full rounded-xl border-2 border-ink bg-white px-4 py-3 text-[16px] focus:border-peri focus:outline-none";
  return (
    <div className="mx-auto grid max-w-5xl items-center gap-10 px-5 py-14 md:grid-cols-[1fr_1.1fr]">
      <div className="hidden md:block">
        <div className="card relative bg-peri-100 p-10">
          <Mascot size={150} mood="wink" />
          <h1 className="mt-6 text-4xl font-extrabold leading-tight">{signUp ? "Welcome aboard." : "Good to see you again."}</h1>
          <p className="mt-3 text-lg text-muted">
            {signUp
              ? "Two minutes from now your first bucket will be under watch. No credit card, no cloud keys."
              : "Your connected accounts and their latest findings are waiting."}
          </p>
        </div>
      </div>

      <div className="card bg-white p-8">
        <h2 className="text-3xl font-extrabold">{signUp ? "Create your account" : "Sign in"}</h2>
        <p className="mt-1 text-muted">{signUp ? "Free during early access." : "Welcome back."}</p>

        {(social.github || social.google) && (
          <div className="mt-6 grid gap-3">
            {social.github && (
              <button type="button" disabled={busy} onClick={() => oauth("github")} className="btn bg-white px-5 py-3">
                Continue with GitHub
              </button>
            )}
            {social.google && (
              <button type="button" disabled={busy} onClick={() => oauth("google")} className="btn bg-white px-5 py-3">
                Continue with Google
              </button>
            )}
            <p className="text-center text-xs font-bold uppercase tracking-wider text-muted">or use email</p>
          </div>
        )}

        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          {signUp && (
            <label className="block text-sm font-bold">
              Your name
              <input className={`${input} mt-1.5 font-normal`} value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" maxLength={60} />
            </label>
          )}
          <label className="block text-sm font-bold">
            Email
            <input className={`${input} mt-1.5 font-normal`} type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" />
          </label>
          <label className="block text-sm font-bold">
            Password
            <input
              className={`${input} mt-1.5 font-normal`}
              type="password"
              required
              minLength={10}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={signUp ? "new-password" : "current-password"}
              aria-describedby="pw-hint"
            />
            {signUp && <span id="pw-hint" className="mt-1 block text-xs font-normal text-muted">At least 10 characters.</span>}
          </label>
          {error && <p role="alert" className="rounded-xl border-2 border-ink bg-coral-100 px-4 py-3 text-sm font-medium text-bad">{error}</p>}
          <button type="submit" disabled={busy} className="btn w-full bg-coral px-6 py-3.5 text-lg text-white">
            {busy ? <Loader2 className="animate-spin" size={20} aria-hidden="true" /> : null}
            {signUp ? "Create account" : "Sign in"}
            {!busy && <ArrowRight size={20} aria-hidden="true" />}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-muted">
          {signUp ? "Already have an account? " : "New here? "}
          <Link className="font-extrabold text-peri underline underline-offset-4" href={signUp ? "/sign-in" : "/sign-up"}>
            {signUp ? "Sign in" : "Create an account"}
          </Link>
        </p>
      </div>
    </div>
  );
}
