"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { adminAuditApi } from "@/entities/audit-log/api";
import { auditLogKeys } from "@/entities/audit-log/model/keys";

export function useAdminAudit(params) {
  return useQuery({
    queryKey: auditLogKeys.list(params),
    queryFn: () => adminAuditApi.list(params).then((r) => r.data),
    staleTime: 15 * 1000,
    placeholderData: keepPreviousData,
  });
}
