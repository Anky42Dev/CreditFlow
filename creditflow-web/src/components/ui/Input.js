import { forwardRef } from "react";

export const Input = forwardRef(function Input(
  { label, error, className = "", id, ...props },
  ref
) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label
          htmlFor={id}
          className="text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          {label}
        </label>
      )}
      <input
        id={id}
        ref={ref}
        className={`rounded-lg border px-3 py-2 text-sm outline-none transition-colors focus:ring-2 focus:ring-blue-500 dark:bg-gray-900 dark:text-gray-100 ${
          error
            ? "border-red-500"
            : "border-gray-300 dark:border-gray-700"
        } ${className}`}
        {...props}
      />
      {error && <span className="text-sm text-red-500">{error}</span>}
    </div>
  );
});
