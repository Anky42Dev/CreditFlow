"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { notificationsApi } from "@/entities/notification/api";
import { notificationKeys } from "@/entities/notification/model/keys";

export function useNotifications(params) {
  return useQuery({
    queryKey: notificationKeys.list(params),
    queryFn: () => notificationsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: notificationKeys.unreadCount,
    queryFn: () =>
      notificationsApi.unreadCount().then((r) => r.data.unread_count),
    staleTime: 30 * 1000,
  });
}
