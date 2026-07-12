const STATUS_OPTIONS = [
  { value: "", label: "Все статусы" },
  { value: "DRAFT", label: "Черновик" },
  { value: "SUBMITTED", label: "Отправлена" },
  { value: "SCORING", label: "Скоринг" },
  { value: "APPROVED", label: "Одобрена" },
  { value: "REJECTED", label: "Отклонена" },
];

export function ApplicationFilters({ status, onStatusChange }) {
  return (
    <div className="flex flex-col gap-1 sm:w-56">
      <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
        Статус
      </label>
      <select
        value={status}
        onChange={(e) => onStatusChange(e.target.value)}
        className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
      >
        {STATUS_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  );
}
