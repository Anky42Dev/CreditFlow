import { Input } from "@/components/ui/Input";

const ORDERING_OPTIONS = [
  { value: "-created_at", label: "Новые" },
  { value: "interest_rate", label: "Ставка ↑" },
  { value: "-interest_rate", label: "Ставка ↓" },
  { value: "-max_amount", label: "Сумма ↓" },
];

export function ProductFilters({ search, ordering, onSearchChange, onOrderingChange }) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <div className="flex-1">
        <Input
          label="Поиск"
          placeholder="Название продукта"
          value={search}
          onChange={(e) => onSearchChange(e.target.value)}
        />
      </div>
      <div className="flex flex-col gap-1">
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          Сортировка
        </label>
        <select
          value={ordering}
          onChange={(e) => onOrderingChange(e.target.value)}
          className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
        >
          {ORDERING_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
