"use client";

import Link from "next/link";
import { useProduct } from "@/entities/product/model/useProducts";
import { Card } from "@/shared/ui/Card";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { DetailSkeleton } from "@/shared/ui/Skeleton";
import { ErrorState } from "@/shared/ui/ErrorState";
import { formatMoney, formatRate } from "@/shared/lib/format";

export function ProductDetail({ id }) {
  const { data: product, isLoading, isError, error, refetch } = useProduct(id);

  if (isLoading) return <DetailSkeleton />;

  if (isError) {
    const notFound = error?.response?.status === 404;
    return (
      <ErrorState
        title={notFound ? "Продукт не найден" : "Что-то пошло не так"}
        description={notFound ? undefined : "Не удалось загрузить продукт"}
        onRetry={notFound ? undefined : refetch}
      />
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Card className="space-y-4">
        <div className="flex items-start justify-between gap-2">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            {product.name}
          </h1>
          <Badge variant="blue">{formatRate(product.interest_rate)}</Badge>
        </div>
        {product.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            {product.description}
          </p>
        )}
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Сумма</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatMoney(product.min_amount)} – {formatMoney(product.max_amount)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Срок</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {product.min_term_months}–{product.max_term_months} мес.
            </dd>
          </div>
        </dl>
        <Link href={`/applications/new?product=${product.id}`}>
          <Button className="w-full">Оформить</Button>
        </Link>
      </Card>
    </div>
  );
}
