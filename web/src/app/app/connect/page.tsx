import type { Metadata } from "next";
import { ConnectWizard } from "@/components/app/ConnectWizard";

export const metadata: Metadata = { title: "Connect AWS" };

export default function ConnectPage() {
  return <ConnectWizard />;
}
