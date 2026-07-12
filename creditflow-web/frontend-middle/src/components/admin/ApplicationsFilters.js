"use client";

import { useEffect, useState } from "react";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { ADMIN_STATUS_OPTIONS } from "@/lib/utils/admin";
import { Input } from "@/components/ui/Input";

export function ApplicationsFilters({ filters, onFieldChange }) {
  const [emailInput, setEmailInput] = useState(filters.user_email || "");
  const [amountInput, setAmountInput] = useState(filters.min_amount || "");
  const debouncedEmail = useDebouncedValue(emailInput);
  const debouncedAmount = useDebouncedValue(amountInput);

  useEffect(() => {
    onFieldChange("user_email", debouncedEmail || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedEmail]);

  useEffect(() => {
    onFieldChange("min_amount", debouncedAmount || undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [debouncedAmount]);

  const toggleStatus = (value) => {
    const current = filters.status || [];
    const next = current.includes(value)
      ? current.filter((s) => s !== value)
      : [...current, value];
    onFieldChange("status", next);
  };

  return (
    <div className="flex flex-wrap items-end gap-4">
      <div className="flex flex-col gap-1">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Статус</span>
        <div className="flex flex-wrap gap-3">
          {ADMIN_STATUS_OPTIONS.map((opt) => (
            <label key={opt.value} className="flex items-center gap-1.5 text-sm text-gray-700 dark:text-gray-300">
              <input
                type="checkbox"
                checked={(filters.status || []).includes(opt.value)}
                onChange={() => toggleStatus(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
      </div>
      <Input
        label="Email клиента"
        value={emailInput}
        onChange={(e) => setEmailInput(e.target.value)}
      />
      <Input
        label="Сумма от"
        type="number"
        value={amountInput}
        onChange={(e) => setAmountInput(e.target.value)}
      />
      <Input
        label="Дата с"
        type="date"
        value={filters.created_from || ""}
        onChange={(e) => onFieldChange("created_from", e.target.value || undefined)}
      />
      <Input
        label="Дата по"
        type="date"
        value={filters.created_to || ""}
        onChange={(e) => onFieldChange("created_to", e.target.value || undefined)}
      />
    </div>
  );
}
