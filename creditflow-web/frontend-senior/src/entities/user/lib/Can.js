"use client";

import { usePermission } from "@/entities/user/lib/usePermission";

export function Can({ perm, children, fallback = null }) {
  return usePermission(perm) ? children : fallback;
}
