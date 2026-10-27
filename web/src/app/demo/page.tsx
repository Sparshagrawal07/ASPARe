import type { Metadata } from "next";
import { DemoApp } from "@/components/demo/DemoApp";

export const metadata: Metadata = {
  title: "Try the demo",
  description: "Break a simulated AWS, Azure or Google Cloud bucket and watch the real ASPARe engine detect, explain, fix and verify it.",
};

export default function DemoPage() {
  return (
    <div className="mx-auto max-w-6xl px-5 py-12">
      <span className="inline-block -rotate-1 rounded-full border-2 border-ink bg-sky px-3 py-1 text-xs font-extrabold uppercase tracking-[0.14em]">Live demo</span>
      <h1 className="mt-4 text-5xl font-extrabold leading-[1.02] sm:text-6xl">Break it. Watch ASPARe fix it.</h1>
      <p className="mt-4 max-w-2xl text-xl text-muted">
        A simulated campus estate across three clouds, powered by the real detection, fusion, remediation and verification
        engine. No account needed.
      </p>
      <div className="mt-10"><DemoApp /></div>
    </div>
  );
}
