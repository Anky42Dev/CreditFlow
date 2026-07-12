"use client";

import { useState } from "react";
import Link from "next/link";
import { useApplications } from "@/entities/application/model/useApplications";
import { ApplicationFilters } from "@/widgets/application-table/ui/ApplicationFilters";
import { ApplicationList } from "@/widgets/application-table/ui/ApplicationList";
import { Button } from "@/shared/ui/Button";

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
      <ApplicationFilters status={status} onStatusChange={handleStatusChange} />
      <ApplicationList
        data={data}
        isLoading={isLoading}
        isError={isError}
        page={page}
        onPageChange={setPage}
        onRetry={refetch}
      />
    </div>
  );
}
