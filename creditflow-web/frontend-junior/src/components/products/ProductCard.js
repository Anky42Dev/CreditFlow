import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { formatMoney, formatRate } from "@/lib/utils/format";

export function ProductCard({ product }) {
  return (
    <Link href={`/products/${product.id}`}>
      <Card className="flex h-full flex-col gap-3 transition-shadow hover:shadow-md">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            {product.name}
          </h3>
          <Badge variant="blue">{formatRate(product.interest_rate)}</Badge>
        </div>
        {product.description && (
          <p className="line-clamp-2 text-sm text-gray-600 dark:text-gray-400">
            {product.description}
          </p>
        )}
        <div className="mt-auto space-y-1 text-sm text-gray-700 dark:text-gray-300">
          <div>
            {formatMoney(product.min_amount)} – {formatMoney(product.max_amount)}
          </div>
          <div>
            {product.min_term_months}–{product.max_term_months} мес.
          </div>
        </div>
      </Card>
    </Link>
  );
}
