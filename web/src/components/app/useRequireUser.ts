"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { type SessionUser, useSessionUser } from "@/lib/session";

/** Returns the signed-in user, or redirects to sign-in. `undefined` while we find out. */
export function useRequireUser(): NonNullable<SessionUser> | undefined {
  const user = useSessionUser();
  const router = useRouter();
  useEffect(() => {
    if (user === null) router.replace("/sign-in");
  }, [user, router]);
  return user ?? undefined;
}
