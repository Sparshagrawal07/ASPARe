import type { Metadata, Viewport } from "next";
import { Suspense } from "react";
import "@fontsource-variable/bricolage-grotesque/wdth.css";
import "@fontsource-variable/inter";
import "@fontsource-variable/jetbrains-mono";
import "./globals.css";
import { Footer } from "@/components/Footer";
import { Wordmark } from "@/components/Logo";
import { Nav } from "@/components/Nav";

export const metadata: Metadata = {
  title: { default: "ASPARe: cloud storage that fixes its own mistakes", template: "%s · ASPARe" },
  description:
    "ASPARe detects misconfigured cloud storage on AWS, Azure and Google Cloud, explains the risk, fixes what is safe to fix, and verifies every fix by re-reading the cloud.",
  applicationName: "ASPARe",
  keywords: ["cloud security", "CSPM", "S3", "Azure Blob", "Google Cloud Storage", "auto-remediation"],
  openGraph: {
    title: "ASPARe: cloud storage that fixes its own mistakes",
    description: "Detect, explain, fix and verify cloud storage misconfigurations across AWS, Azure and GCP.",
    type: "website",
  },
};

export const viewport: Viewport = { themeColor: "#fffbf3", colorScheme: "light" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 btn bg-white px-4 py-2"
        >
          Skip to content
        </a>
        <Suspense
          fallback={
            <header className="sticky top-0 z-40 h-[68px] border-b-2 border-ink bg-paper/95">
              <div className="mx-auto flex h-full max-w-6xl items-center px-5">
                <Wordmark />
              </div>
            </header>
          }
        >
          <Nav />
        </Suspense>
        <main id="main" className="flex-1">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
