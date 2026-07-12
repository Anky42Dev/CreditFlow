"use client";

import { useQuery, useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import { adminApplicationsApi } from "@/entities/application/api/admin";
import { adminApplicationKeys } from "@/entities/application/model/keys";

export function useAdminApplications(params) {
  return useQuery({
    queryKey: adminApplicationKeys.list(params),
    queryFn: () => adminApplicationsApi.list(params).then((r) => r.data),
    staleTime: 15 * 1000,
    placeholderData: keepPreviousData,
  });
}

/**
 * Infinite-scroll variant for the admin applications list (DOC 4 §9.1, AC-7).
 * Keyed under the same adminApplicationKeys.all prefix as useAdminApplications
 * so the existing WS/mutation invalidation (adminApplicationKeys.all) also covers it.
 */
export function useInfiniteAdminApplications(params) {
  return useInfiniteQuery({
    queryKey: adminApplicationKeys.infiniteList(params),
    queryFn: ({ pageParam }) =>
      adminApplicationsApi.list({ ...params, page: pageParam }).then((r) => r.data),
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
    initialPageParam: 1,
    staleTime: 15 * 1000,
  });
}

export function useAdminApplication(id) {
  return useQuery({
    queryKey: adminApplicationKeys.detail(id),
    queryFn: () => adminApplicationsApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}
