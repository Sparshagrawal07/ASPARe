import type { Metadata } from "next";
import { Suspense } from "react";
import { ConnectionView } from "@/components/app/ConnectionView";

export const metadata: Metadata = { title: "Account" };

export default async function ConnectionPage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<p className="px-5 py-20 text-center text-muted">Loading...</p>}>
      <Resolved params={params} />
    </Suspense>
  );
}

async function Resolved({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ConnectionView id={id} />;
}
