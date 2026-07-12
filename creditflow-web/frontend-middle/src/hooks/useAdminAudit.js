"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { adminAuditApi } from "@/lib/api/admin";

export function useAdminAudit(params) {
  return useQuery({
    queryKey: ["admin-audit", params],
    queryFn: () => adminAuditApi.list(params).then((r) => r.data),
    staleTime: 15 * 1000,
    placeholderData: keepPreviousData,
  });
}
