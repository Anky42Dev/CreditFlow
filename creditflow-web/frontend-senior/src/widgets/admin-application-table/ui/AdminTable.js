import { RowListSkeleton } from "@/shared/ui/Skeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorState } from "@/shared/ui/ErrorState";
import { Button } from "@/shared/ui/Button";

const PAGE_SIZE = 20;

/** Shared table shell (columns/pagination/loading states) for the admin CRUD screens. */
export function AdminTable({
  columns,
  data,
  isLoading,
  isError,
  onRetry,
  page,
  onPageChange,
  emptyTitle = "Нет данных",
  renderRow,
}) {
  if (isLoading) return <RowListSkeleton />;
  if (isError) {
    return <ErrorState description="Не удалось загрузить данные" onRetry={onRetry} />;
  }

  const results = data?.results || [];
  if (results.length === 0) return <EmptyState title={emptyTitle} />;

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto rounded-xl border border-gray-200 dark:border-gray-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800/50 dark:text-gray-400">
            <tr>
              {columns.map((col) => (
                <th key={col.key} className="whitespace-nowrap px-4 py-3 font-medium">
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
            {results.map((row) => renderRow(row))}
          </tbody>
        </table>
      </div>
      {onPageChange && totalPages > 1 && (
        <div className="flex items-center justify-center gap-3">
          <Button
            variant="secondary"
            disabled={!data?.previous}
            onClick={() => onPageChange(page - 1)}
          >
            Назад
          </Button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {page} / {totalPages}
          </span>
          <Button
            variant="secondary"
            disabled={!data?.next}
            onClick={() => onPageChange(page + 1)}
          >
            Вперёд
          </Button>
        </div>
      )}
    </div>
  );
}
