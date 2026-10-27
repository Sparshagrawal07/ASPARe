"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

export type SessionUser = { id: string; email: string; name: string } | null;

/** Lightweight session hook: asks the server who we are. `undefined` while loading. */
export function useSessionUser(): SessionUser | undefined {
  const [user, setUser] = useState<SessionUser | undefined>(undefined);
  const path = usePathname(); // re-check after sign-in/out navigations
  useEffect(() => {
    let alive = true;
    fetch("/api/me", { cache: "no-store" })
      .then((r) => (r.ok ? r.json() : { user: null }))
      .then((d) => alive && setUser(d.user ?? null))
      .catch(() => alive && setUser(null));
    return () => {
      alive = false;
    };
  }, [path]);
  return user;
}
