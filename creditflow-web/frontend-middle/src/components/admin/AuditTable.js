"use client";

import { Fragment, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { AdminTable } from "@/components/admin/AdminTable";

const COLUMNS = [
  { key: "created", label: "Дата" },
  { key: "actor", label: "Автор" },
  { key: "action", label: "Действие" },
  { key: "object", label: "Объект" },
  { key: "expand", label: "" },
];

export default function AuditTable({ data, isLoading, isError, onRetry, page, onPageChange }) {
  const [expandedId, setExpandedId] = useState(null);

  return (
    <AdminTable
      columns={COLUMNS}
      data={data}
      isLoading={isLoading}
      isError={isError}
      onRetry={onRetry}
      page={page}
      onPageChange={onPageChange}
      emptyTitle="Записей не найдено"
      renderRow={(log) => {
        const isExpanded = expandedId === log.id;
        return (
          <Fragment key={log.id}>
            <tr>
              <td className="whitespace-nowrap px-4 py-3 text-gray-500 dark:text-gray-400">
                {new Date(log.created_at).toLocaleString("ru-RU")}
              </td>
              <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                {log.actor_email || "система"}
              </td>
              <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">
                {log.action}
              </td>
              <td className="px-4 py-3 text-gray-700 dark:text-gray-300">
                {log.object_type} #{log.object_id}
              </td>
              <td className="px-4 py-3 text-right">
                <button
                  onClick={() => setExpandedId(isExpanded ? null : log.id)}
                  className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
                  aria-label="Показать изменения"
                >
                  {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
              </td>
            </tr>
            {isExpanded && (
              <tr>
                <td colSpan={5} className="bg-gray-50 px-4 py-3 dark:bg-gray-800/50">
                  <pre className="overflow-x-auto text-xs text-gray-700 dark:text-gray-300">
                    {JSON.stringify(log.changes, null, 2)}
                  </pre>
                </td>
              </tr>
            )}
          </Fragment>
        );
      }}
    />
  );
}
