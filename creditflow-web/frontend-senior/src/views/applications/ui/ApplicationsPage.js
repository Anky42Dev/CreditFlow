"use client";

import { useState } from "react";
import Link from "next/link";
import { useApplications } from "@/entities/application/model/useApplications";
import { ApplicationFilters } from "@/widgets/application-table/ui/ApplicationFilters";
import { ApplicationList } from "@/widgets/application-table/ui/ApplicationList";
import { Button } from "@/shared/ui/Button";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function ApplicationsPage() {
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useApplications({
    status: status || undefined,
    ordering: "-created_at",
    page,
  });

  const handleStatusChange = (value) => {
    setStatus(value);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Мои заявки
        </h1>
        <Link href="/applications/new">
          <Button>Новая заявка</Button>
        </Link>
      </div>
      <WidgetErrorBoundary name="application-filters">
        <ApplicationFilters status={status} onStatusChange={handleStatusChange} />
      </WidgetErrorBoundary>
      <WidgetErrorBoundary name="application-list">
        <ApplicationList
          data={data}
          isLoading={isLoading}
          isError={isError}
          page={page}
          onPageChange={setPage}
          onRetry={refetch}
        />
      </WidgetErrorBoundary>
    </div>
  );
}
