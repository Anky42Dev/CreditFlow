"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { notificationsApi } from "@/entities/notification/api";
import { notificationKeys } from "@/entities/notification/model/keys";

export function useReadNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => notificationsApi.read(id).then((r) => r.data),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: notificationKeys.unreadCount });
      const prevCount = qc.getQueryData(notificationKeys.unreadCount);
      qc.setQueryData(notificationKeys.unreadCount, (n) => Math.max(0, (n ?? 1) - 1));
      return { prevCount };
    },
    onError: (err, id, ctx) => {
      if (ctx) qc.setQueryData(notificationKeys.unreadCount, ctx.prevCount);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount });
    },
  });
}

export function useReadAllNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.readAll().then((r) => r.data),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: notificationKeys.unreadCount });
      const prevCount = qc.getQueryData(notificationKeys.unreadCount);
      qc.setQueryData(notificationKeys.unreadCount, 0);
      return { prevCount };
    },
    onError: (err, vars, ctx) => {
      if (ctx) qc.setQueryData(notificationKeys.unreadCount, ctx.prevCount);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: notificationKeys.all });
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount });
    },
  });
}
