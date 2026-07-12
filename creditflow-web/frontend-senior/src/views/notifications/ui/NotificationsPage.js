"use client";

import { useState } from "react";
import { useNotifications } from "@/entities/notification/model/useNotifications";
import {
  useReadNotification,
  useReadAllNotifications,
} from "@/features/mark-read/model/useMarkRead";
import { NotificationFilters } from "@/widgets/notification-list/ui/NotificationFilters";
import { NotificationList } from "@/widgets/notification-list/ui/NotificationList";
import { Button } from "@/shared/ui/Button";

export function NotificationsPage() {
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
