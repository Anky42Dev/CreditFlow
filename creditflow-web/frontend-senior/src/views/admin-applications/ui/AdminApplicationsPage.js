"use client";

import { Suspense, useState } from "react";
import { useInfiniteAdminApplications } from "@/entities/application/model/useAdminApplications";
import { useUrlFilters } from "@/shared/lib/useUrlFilters";
import { ApplicationsFilters } from "@/widgets/admin-application-table/ui/ApplicationsFilters";
import { InfiniteApplicationsList } from "@/widgets/admin-application-table/ui/InfiniteApplicationsList";
import { RowListSkeleton } from "@/shared/ui/Skeleton";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

const TABS = [
  { key: "all", label: "Все заявки" },
  { key: "queue", label: "Очередь (ручная проверка)" },
];

const ARRAY_KEYS = ["status"];

function AdminApplicationsPageInner() {
  const [tab, setTab] = useState("all");
  const { filters, setField } = useUrlFilters(ARRAY_KEYS);

  const isQueue = tab === "queue";
  const {
    data,
    isLoading,
    isError,
    refetch,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteAdminApplications(
    isQueue
      ? { status: ["MANUAL_REVIEW"], ordering: "submitted_at" }
      : { ...filters, ordering: "-created_at" }
  );

  const items = data?.pages.flatMap((p) => p.results) ?? [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Заявки</h1>
      <div className="flex gap-2 border-b border-gray-200 dark:border-gray-800">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium ${
              tab === t.key
                ? "border-b-2 border-blue-600 text-blue-600 dark:text-blue-400"
                : "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>
      {!isQueue && (
        <WidgetErrorBoundary name="admin-applications-filters">
          <ApplicationsFilters filters={filters} onFieldChange={setField} />
        </WidgetErrorBoundary>
      )}
      <WidgetErrorBoundary name="admin-applications-list">
        <InfiniteApplicationsList
          items={items}
          isLoading={isLoading}
          isError={isError}
          onRetry={refetch}
          hasNextPage={hasNextPage}
          isFetchingNextPage={isFetchingNextPage}
          fetchNextPage={fetchNextPage}
          showWaiting={isQueue}
          emptyTitle={isQueue ? "Очередь пуста" : "Заявок не найдено"}
        />
      </WidgetErrorBoundary>
    </div>
  );
}

export function AdminApplicationsPage() {
  return (
    <Suspense fallback={<RowListSkeleton />}>
      <AdminApplicationsPageInner />
    </Suspense>
  );
}
