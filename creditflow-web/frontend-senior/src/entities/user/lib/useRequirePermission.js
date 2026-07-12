"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePermission } from "./usePermission";

/** Redirects away from admin sub-pages the current user's role can enter but lacks the specific permission for (e.g. SUPPORT/UNDERWRITER on /admin/products). */
export function useRequirePermission(perm, redirectTo = "/admin/applications") {
  const allowed = usePermission(perm);
  const router = useRouter();

  useEffect(() => {
    if (!allowed) router.replace(redirectTo);
  }, [allowed, redirectTo, router]);

  return allowed;
}
