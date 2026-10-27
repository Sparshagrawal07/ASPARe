import type { Metadata } from "next";
import { Overview } from "@/components/app/Overview";

export const metadata: Metadata = { title: "Dashboard" };

export default function AppPage() {
  return <Overview />;
}
