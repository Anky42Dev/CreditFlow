"use client";

import { usePermission } from "@/hooks/usePermission";

export function Can({ perm, children, fallback = null }) {
  return usePermission(perm) ? children : fallback;
}
