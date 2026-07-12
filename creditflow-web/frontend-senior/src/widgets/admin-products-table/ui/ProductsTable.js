import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { AdminTable } from "@/widgets/admin-application-table/ui/AdminTable";
import { formatMoney, formatRate } from "@/shared/lib/format";

const COLUMNS = [
  { key: "name", label: "Название" },
  { key: "amount", label: "Сумма" },
  { key: "rate", label: "Ставка" },
  { key: "term", label: "Срок" },
  { key: "status", label: "Статус" },
  { key: "actions", label: "" },
];

export function ProductsTable({
  data,
  isLoading,
  isError,
  onRetry,
  page,
  onPageChange,
  onEdit,
  onDeactivate,
  deactivatingId,
}) {
  return (
    <AdminTable
      columns={COLUMNS}
      data={data}
      isLoading={isLoading}
      isError={isError}
      onRetry={onRetry}
      page={page}
      onPageChange={onPageChange}
      emptyTitle="Продуктов пока нет"
      renderRow={(product) => (
        <tr key={product.id}>
          <td className="px-4 py-3">
            <div className="font-medium text-gray-900 dark:text-gray-100">{product.name}</div>
            <div className="text-xs text-gray-500 dark:text-gray-400">{product.slug}</div>
          </td>
          <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
            {formatMoney(product.min_amount)} – {formatMoney(product.max_amount)}
          </td>
          <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
            {formatRate(product.interest_rate)}
          </td>
          <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
            {product.min_term_months}–{product.max_term_months} мес.
          </td>
          <td className="px-4 py-3">
            <Badge variant={product.is_active ? "green" : "gray"}>
              {product.is_active ? "Активен" : "Неактивен"}
            </Badge>
          </td>
          <td className="px-4 py-3">
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => onEdit(product)}>
                Редактировать
              </Button>
              {product.is_active && (
                <Button
                  variant="danger"
                  disabled={deactivatingId === product.id}
                  onClick={() => onDeactivate(product.id)}
                >
                  Деактивировать
                </Button>
              )}
            </div>
          </td>
        </tr>
      )}
    />
  );
}
