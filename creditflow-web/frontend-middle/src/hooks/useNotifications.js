"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { notificationsApi } from "@/lib/api/notifications";

export function useNotifications(params) {
  return useQuery({
    queryKey: ["notifications", params],
    queryFn: () => notificationsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useUnreadCount() {
  return useQuery({
    queryKey: ["unread-count"],
    queryFn: () =>
      notificationsApi.unreadCount().then((r) => r.data.unread_count),
    staleTime: 30 * 1000,
  });
}

export function useReadNotification() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id) => notificationsApi.read(id).then((r) => r.data),
    onMutate: async (id) => {
      await qc.cancelQueries({ queryKey: ["unread-count"] });
      const prevCount = qc.getQueryData(["unread-count"]);
      qc.setQueryData(["unread-count"], (n) => Math.max(0, (n ?? 1) - 1));
      return { prevCount };
    },
    onError: (err, id, ctx) => {
      if (ctx) qc.setQueryData(["unread-count"], ctx.prevCount);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["unread-count"] });
    },
  });
}

export function useReadAllNotifications() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => notificationsApi.readAll().then((r) => r.data),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["unread-count"] });
      const prevCount = qc.getQueryData(["unread-count"]);
      qc.setQueryData(["unread-count"], 0);
      return { prevCount };
    },
    onError: (err, vars, ctx) => {
      if (ctx) qc.setQueryData(["unread-count"], ctx.prevCount);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["notifications"] });
      qc.invalidateQueries({ queryKey: ["unread-count"] });
    },
  });
}
