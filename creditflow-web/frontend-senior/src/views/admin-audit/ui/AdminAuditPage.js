"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";
import { useRequirePermission } from "@/entities/user/lib/useRequirePermission";
import { PERMISSIONS } from "@/shared/config/permissions";
import { useAdminAudit } from "@/entities/audit-log/model/useAuditLog";
import { useUrlFilters } from "@/shared/lib/useUrlFilters";
import { AuditFilters } from "@/widgets/admin-audit-table/ui/AuditFilters";
import { RowListSkeleton } from "@/shared/ui/Skeleton";
import { DetailSkeleton } from "@/shared/ui/Skeleton";

const AuditTable = dynamic(() => import("@/widgets/admin-audit-table/ui/AuditTable"), {
  loading: () => <RowListSkeleton />,
  ssr: false,
});

function AdminAuditPageInner() {
  const allowed = useRequirePermission(PERMISSIONS.AUDIT_VIEW);
  const { filters, page, setField, setPage } = useUrlFilters();

  const { data, isLoading, isError, refetch } = useAdminAudit({ ...filters, page });

  if (!allowed) return <DetailSkeleton />;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Аудит-лог</h1>
      <AuditFilters filters={filters} onFieldChange={setField} />
      <AuditTable
        data={data}
        isLoading={isLoading}
        isError={isError}
        onRetry={refetch}
        page={page}
        onPageChange={setPage}
      />
    </div>
  );
}

export function AdminAuditPage() {
  return (
    <Suspense fallback={<RowListSkeleton />}>
      <AdminAuditPageInner />
    </Suspense>
  );
}
