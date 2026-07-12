import { Badge } from "@/shared/ui/Badge";
import { formatMoney } from "@/shared/lib/format";

const STATUS_MAP = {
  PAID: { label: "Оплачен", variant: "green" },
  PENDING: { label: "Ожидается", variant: "gray" },
  OVERDUE: { label: "Просрочен", variant: "red" },
};

const ROW_CLASS = {
  PAID: "",
  PENDING: "",
  OVERDUE: "bg-red-50 dark:bg-red-900/10",
};

export function ScheduleTable({ items }) {
  if (!items?.length) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-gray-500 dark:border-gray-800 dark:text-gray-400">
            <th className="px-3 py-2 font-medium">#</th>
            <th className="px-3 py-2 font-medium">Дата платежа</th>
            <th className="px-3 py-2 font-medium">Сумма</th>
            <th className="px-3 py-2 font-medium">Статус</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => {
            const { label, variant } = STATUS_MAP[item.status] || {
              label: item.status,
              variant: "gray",
            };
            return (
              <tr
                key={item.id}
                className={`border-b border-gray-100 dark:border-gray-800 ${ROW_CLASS[item.status] || ""}`}
              >
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">{item.sequence}</td>
                <td className="px-3 py-2 text-gray-700 dark:text-gray-300">
                  {new Date(item.due_date).toLocaleDateString("ru-RU")}
                </td>
                <td className="px-3 py-2 font-medium text-gray-900 dark:text-gray-100">
                  {formatMoney(item.amount)}
                </td>
                <td className="px-3 py-2">
                  <Badge variant={variant}>{label}</Badge>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
