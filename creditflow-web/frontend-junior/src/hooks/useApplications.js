"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { applicationsApi } from "@/lib/api/applications";

export function useApplications(params) {
  return useQuery({
    queryKey: ["applications", params],
    queryFn: () => applicationsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useApplication(id) {
  return useQuery({
    queryKey: ["application", id],
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
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}

export function useUpdateApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => applicationsApi.update(id, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application", id] });
    },
  });
}

export function useSubmitApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationsApi.submit(id).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["application", id] });
    },
  });
}

export function useDeleteApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationsApi.remove(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });
}
