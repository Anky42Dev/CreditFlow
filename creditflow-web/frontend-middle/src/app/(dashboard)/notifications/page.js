"use client";

import { useState } from "react";
import {
  useNotifications,
  useReadNotification,
  useReadAllNotifications,
} from "@/hooks/useNotifications";
import { NotificationFilters } from "@/components/notifications/NotificationFilters";
import { NotificationList } from "@/components/notifications/NotificationList";
import { Button } from "@/components/ui/Button";

export default function NotificationsPage() {
  const [isRead, setIsRead] = useState("");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useNotifications({
    is_read: isRead || undefined,
    page,
  });
  const readNotification = useReadNotification();
  const readAll = useReadAllNotifications();

  const handleFilterChange = (value) => {
    setIsRead(value);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Уведомления
        </h1>
        <Button
          variant="secondary"
          onClick={() => readAll.mutate()}
          disabled={readAll.isPending}
        >
          Прочитать всё
        </Button>
      </div>
      <NotificationFilters isRead={isRead} onChange={handleFilterChange} />
      <NotificationList
        data={data}
        isLoading={isLoading}
        isError={isError}
        page={page}
        onPageChange={setPage}
        onRetry={refetch}
        onRead={readNotification.mutate}
      />
    </div>
  );
}
