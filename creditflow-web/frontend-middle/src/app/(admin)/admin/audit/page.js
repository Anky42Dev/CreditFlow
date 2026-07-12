"use client";

import { Suspense } from "react";
import dynamic from "next/dynamic";
import { useRequirePermission } from "@/hooks/useRequirePermission";
import { PERMISSIONS } from "@/lib/rbac/permissions";
import { useAdminAudit } from "@/hooks/useAdminAudit";
import { useUrlFilters } from "@/hooks/useUrlFilters";
import { AuditFilters } from "@/components/admin/AuditFilters";
import { RowListSkeleton } from "@/components/feedback/Skeleton";
import { DetailSkeleton } from "@/components/feedback/Skeleton";

const AuditTable = dynamic(() => import("@/components/admin/AuditTable"), {
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

export default function AdminAuditPage() {
  return (
    <Suspense fallback={<RowListSkeleton />}>
      <AdminAuditPageInner />
    </Suspense>
  );
}
