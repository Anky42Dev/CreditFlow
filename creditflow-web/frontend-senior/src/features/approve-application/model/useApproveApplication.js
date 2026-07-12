"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { adminApplicationsApi } from "@/entities/application/api/admin";
import { adminApplicationKeys } from "@/entities/application/model/keys";

function useInvalidateAdminApplication(id) {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: adminApplicationKeys.all });
    qc.invalidateQueries({ queryKey: adminApplicationKeys.detail(id) });
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
