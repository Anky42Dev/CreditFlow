"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { useVirtualizer } from "@tanstack/react-virtual";
import { StatusBadge } from "@/components/applications/StatusBadge";
import { RowListSkeleton } from "@/components/feedback/Skeleton";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { formatMoney } from "@/lib/utils/format";
import { formatWaitTime } from "@/lib/utils/admin";

const ROW_HEIGHT = 52;
const VIEWPORT_HEIGHT = 560;

function gridClass(showWaiting) {
  return showWaiting
    ? "grid-cols-[80px_1fr_140px_100px_160px_140px_140px]"
    : "grid-cols-[80px_1fr_140px_100px_160px_140px]";
}

/**
 * Virtualized + infinite-scroll replacement for the paginated ApplicationsTable
 * (DOC 4 §9.1/§9.3, AC-7). Renders only the rows in view via @tanstack/react-virtual
 * while an IntersectionObserver sentinel triggers fetchNextPage near the bottom.
 */
export function InfiniteApplicationsList({
  items,
  isLoading,
  isError,
  onRetry,
  hasNextPage,
  isFetchingNextPage,
  fetchNextPage,
  showWaiting = false,
  emptyTitle = "Заявок не найдено",
}) {
  const scrollRef = useRef(null);
  const sentinelRef = useRef(null);
  const columns = gridClass(showWaiting);

  const rowVirtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  });

  useEffect(() => {
    const sentinel = sentinelRef.current;
    const root = scrollRef.current;
    if (!sentinel || !root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { root, rootMargin: "200px" }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage, items.length]);

  if (isLoading) return <RowListSkeleton />;
  if (isError) {
    return <ErrorState description="Не удалось загрузить данные" onRetry={onRetry} />;
  }
  if (items.length === 0) return <EmptyState title={emptyTitle} />;

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-800">
      <div
        className={`grid ${columns} gap-2 border-b border-gray-200 bg-gray-50 px-4 py-3 text-xs font-medium uppercase text-gray-500 dark:border-gray-800 dark:bg-gray-800/50 dark:text-gray-400`}
      >
        <span>№</span>
        <span>Клиент</span>
        <span>Сумма</span>
        <span>Срок</span>
        <span>Статус</span>
        <span>Создана</span>
        {showWaiting && <span>Ожидание</span>}
      </div>
      <div ref={scrollRef} style={{ height: VIEWPORT_HEIGHT, overflow: "auto" }}>
        <div style={{ height: rowVirtualizer.getTotalSize(), position: "relative" }}>
          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const application = items[virtualRow.index];
            return (
              <div
                key={application.id}
                className={`grid ${columns} items-center gap-2 border-b border-gray-100 px-4 text-sm dark:border-gray-800`}
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: virtualRow.size,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <Link
                  href={`/admin/applications/${application.id}`}
                  className="font-medium text-blue-600 hover:underline dark:text-blue-400"
                >
                  №{application.id}
                </Link>
                <span className="truncate text-gray-700 dark:text-gray-300">
                  {application.user_email}
                </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {formatMoney(application.amount)}
                </span>
                <span className="text-gray-700 dark:text-gray-300">
                  {application.term_months} мес.
                </span>
                <StatusBadge status={application.status} />
                <span className="text-gray-500 dark:text-gray-400">
                  {new Date(application.created_at).toLocaleDateString("ru-RU")}
                </span>
                {showWaiting && (
                  <span className="text-gray-700 dark:text-gray-300">
                    {formatWaitTime(application.submitted_at)}
                  </span>
                )}
              </div>
            );
          })}
        </div>
        <div ref={sentinelRef} style={{ height: 1 }} />
        {isFetchingNextPage && (
          <div className="py-3 text-center text-sm text-gray-500 dark:text-gray-400">
            Загрузка…
          </div>
        )}
      </div>
    </div>
  );
}
