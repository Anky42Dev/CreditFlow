const FILTERS = [
  { value: "", label: "Все" },
  { value: "false", label: "Непрочитанные" },
  { value: "true", label: "Прочитанные" },
];

export function NotificationFilters({ isRead, onChange }) {
  return (
    <div className="flex gap-2">
      {FILTERS.map((f) => (
        <button
          key={f.value}
          type="button"
          onClick={() => onChange(f.value)}
          className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
            isRead === f.value
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
          }`}
        >
          {f.label}
        </button>
      ))}
    </div>
  );
}
