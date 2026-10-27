"use client";

import { Menu, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { useSessionUser } from "@/lib/session";
import { Wordmark } from "./Logo";

const LINKS = [
  { href: "/demo", label: "Try the demo" },
  { href: "/connect", label: "How it connects" },
  { href: "/trust", label: "Trust and safety" },
];

export function Nav() {
  const path = usePathname();
  const user = useSessionUser();
  const [open, setOpen] = useState(false);
  const cta = user ? { href: "/app", label: "Open dashboard" } : { href: "/sign-up", label: "Start free" };
  return (
    <header className="sticky top-0 z-40 border-b-2 border-ink bg-paper/95 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-[68px] max-w-6xl items-center justify-between px-5">
        <Link href="/" aria-label="ASPARe home" className="rounded-lg">
          <Wordmark />
        </Link>
        <ul className="hidden items-center gap-1 md:flex">
          {LINKS.map((l) => (
            <li key={l.href}>
              <Link
                href={l.href}
                aria-current={path === l.href ? "page" : undefined}
                className={`rounded-lg px-3.5 py-2 text-[15px] font-semibold transition-colors hover:bg-sun-100 ${
                  path === l.href ? "bg-sun-100 text-ink" : "text-muted hover:text-ink"
                }`}
              >
                {l.label}
              </Link>
            </li>
          ))}
          {!user && user !== undefined && (
            <li>
              <Link href="/sign-in" className="rounded-lg px-3.5 py-2 text-[15px] font-semibold text-muted hover:bg-sun-100 hover:text-ink">
                Sign in
              </Link>
            </li>
          )}
          <li className="ml-2">
            <Link href={cta.href} className="btn bg-peri px-5 py-2.5 text-[15px] text-white">
              {cta.label}
            </Link>
          </li>
        </ul>
        <button
          type="button"
          className="btn bg-white p-2 md:hidden"
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label="Toggle menu"
          onClick={() => setOpen((v) => !v)}
        >
          {open ? <X size={22} /> : <Menu size={22} />}
        </button>
      </nav>
      {open && (
        <ul id="mobile-menu" className="border-t-2 border-ink bg-paper px-5 pb-4 md:hidden">
          {[...LINKS, ...(user ? [] : [{ href: "/sign-in", label: "Sign in" }]), cta].map((l) => (
            <li key={l.href}>
              <Link href={l.href} onClick={() => setOpen(false)} className="block rounded-lg px-3 py-3 font-semibold hover:bg-sun-100">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </header>
  );
}
