import { RowListSkeleton } from "@/shared/ui/Skeleton";
import { EmptyState } from "@/shared/ui/EmptyState";
import { ErrorState } from "@/shared/ui/ErrorState";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { NotificationItem } from "@/entities/notification/ui/NotificationItem";

const PAGE_SIZE = 20;

export function NotificationList({
  data,
  isLoading,
  isError,
  page,
  onPageChange,
  onRetry,
  onRead,
}) {
  if (isLoading) return <RowListSkeleton />;

  if (isError) {
    return <ErrorState description="Не удалось загрузить уведомления" onRetry={onRetry} />;
  }

  const results = data?.results || [];

  if (results.length === 0) {
    return <EmptyState title="Уведомлений нет" />;
  }

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <Card className="divide-y divide-gray-100 p-2 dark:divide-gray-800">
        {results.map((n) => (
          <NotificationItem key={n.id} notification={n} onRead={onRead} />
        ))}
      </Card>
      {totalPages > 1 && (
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
