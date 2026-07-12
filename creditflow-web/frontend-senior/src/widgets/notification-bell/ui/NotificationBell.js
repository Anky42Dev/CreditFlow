"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell } from "lucide-react";
import { useNotifications, useUnreadCount } from "@/entities/notification/model/useNotifications";
import { useReadNotification } from "@/features/mark-read/model/useMarkRead";
import { NotificationItem } from "@/entities/notification/ui/NotificationItem";
import { EmptyState } from "@/shared/ui/EmptyState";

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);

  const { data: unreadCount } = useUnreadCount();
  const { data, isLoading } = useNotifications({ page_size: 5 });
  const readNotification = useReadNotification();

  useEffect(() => {
    if (!open) return;
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open]);

  const results = data?.results || [];
  const count = unreadCount ?? 0;

  return (
    <div ref={containerRef} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
        aria-label="Уведомления"
      >
        <Bell size={20} />
        {count > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-semibold text-white">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-gray-200 bg-white shadow-lg dark:border-gray-800 dark:bg-gray-900">
          <div className="border-b border-gray-100 px-3 py-2 text-sm font-semibold text-gray-900 dark:border-gray-800 dark:text-gray-100">
            Уведомления
          </div>
          <div className="max-h-96 overflow-y-auto p-2">
            {isLoading && (
              <p className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400">Загрузка…</p>
            )}
            {!isLoading && results.length === 0 && (
              <EmptyState title="Нет уведомлений" />
            )}
            {!isLoading &&
              results.map((n) => (
                <NotificationItem
                  key={n.id}
                  notification={n}
                  onRead={readNotification.mutate}
                  onAfterClick={() => setOpen(false)}
                  compact
                />
              ))}
          </div>
          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="block border-t border-gray-100 px-3 py-2 text-center text-sm font-medium text-blue-600 hover:bg-gray-50 dark:border-gray-800 dark:text-blue-400 dark:hover:bg-gray-800"
          >
            Все уведомления
          </Link>
        </div>
      )}
    </div>
  );
}
