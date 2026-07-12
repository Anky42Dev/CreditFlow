"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { applicationsApi } from "@/entities/application/api";
import { applicationKeys } from "@/entities/application/model/keys";

export function useApplications(params) {
  return useQuery({
    queryKey: applicationKeys.list(params),
    queryFn: () => applicationsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useApplication(id) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => applicationsApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

export function useCreateApplication() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => applicationsApi.create(data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}

export function useUpdateApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => applicationsApi.update(id, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: applicationKeys.all });
      qc.invalidateQueries({ queryKey: applicationKeys.detail(id) });
    },
  });
}

export function useDeleteApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: applicationKeys.all });
    },
  });
}
