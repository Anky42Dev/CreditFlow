import { RowListSkeleton } from "@/components/feedback/Skeleton";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Button } from "@/components/ui/Button";
import { LoanCard } from "./LoanCard";

const PAGE_SIZE = 20;

export function LoanList({ data, isLoading, isError, page, onPageChange, onRetry }) {
  if (isLoading) {
    return <RowListSkeleton />;
  }

  if (isError) {
    return <ErrorState description="Не удалось загрузить договоры" onRetry={onRetry} />;
  }

  const results = data?.results || [];

  if (results.length === 0) {
    return <EmptyState title="Договоров пока нет" />;
  }

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="space-y-3">
        {results.map((loan) => (
          <LoanCard key={loan.id} loan={loan} />
        ))}
      </div>
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
