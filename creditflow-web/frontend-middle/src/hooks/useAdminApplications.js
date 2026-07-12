"use client";

import {
  useQuery,
  useMutation,
  useQueryClient,
  useInfiniteQuery,
  keepPreviousData,
} from "@tanstack/react-query";
import { adminApplicationsApi } from "@/lib/api/admin";

export function useAdminApplications(params) {
  return useQuery({
    queryKey: ["admin-applications", params],
    queryFn: () => adminApplicationsApi.list(params).then((r) => r.data),
    staleTime: 15 * 1000,
    placeholderData: keepPreviousData,
  });
}

/**
 * Infinite-scroll variant for the admin applications list (DOC 4 §9.1, AC-7).
 * Keyed under the same ["admin-applications", ...] prefix as useAdminApplications
 * so the existing WS/mutation invalidation (["admin-applications"]) also covers it.
 */
export function useInfiniteAdminApplications(params) {
  return useInfiniteQuery({
    queryKey: ["admin-applications", "infinite", params],
    queryFn: ({ pageParam }) =>
      adminApplicationsApi.list({ ...params, page: pageParam }).then((r) => r.data),
    getNextPageParam: (last, pages) => (last.next ? pages.length + 1 : undefined),
    initialPageParam: 1,
    staleTime: 15 * 1000,
  });
}

export function useAdminApplication(id) {
  return useQuery({
    queryKey: ["admin-application", id],
    queryFn: () => adminApplicationsApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 15 * 1000,
  });
}

function useInvalidateAdminApplication(id) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["admin-applications"] });
    qc.invalidateQueries({ queryKey: ["admin-application", id] });
  };
}

export function useApproveApplication(id) {
  const invalidate = useInvalidateAdminApplication(id);
  return useMutation({
    mutationFn: (data) => adminApplicationsApi.approve(id, data).then((r) => r.data),
    onSuccess: invalidate,
  });
}

export function useRejectApplication(id) {
  const invalidate = useInvalidateAdminApplication(id);
  return useMutation({
    mutationFn: (data) => adminApplicationsApi.reject(id, data).then((r) => r.data),
    onSuccess: invalidate,
  });
}

export function useRequestDocuments(id) {
  const invalidate = useInvalidateAdminApplication(id);
  return useMutation({
    mutationFn: () => adminApplicationsApi.requestDocuments(id).then((r) => r.data),
    onSuccess: invalidate,
  });
}
