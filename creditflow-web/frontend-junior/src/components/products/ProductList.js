import { ListSkeleton } from "@/components/feedback/Skeleton";
import { EmptyState } from "@/components/feedback/EmptyState";
import { ErrorState } from "@/components/feedback/ErrorState";
import { Button } from "@/components/ui/Button";
import { ProductCard } from "./ProductCard";

const PAGE_SIZE = 20;

export function ProductList({ data, isLoading, isError, page, onPageChange, onRetry }) {
  if (isLoading) {
    return <ListSkeleton />;
  }

  if (isError) {
    return (
      <ErrorState description="Не удалось загрузить продукты" onRetry={onRetry} />
    );
  }

  const results = data?.results || [];

  if (results.length === 0) {
    return <EmptyState title="Продукты не найдены" />;
  }

  const totalPages = Math.max(1, Math.ceil((data?.count || 0) / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {results.map((product) => (
          <ProductCard key={product.id} product={product} />
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
