"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { profileApi } from "@/entities/user/api/profile";
import { profileKeys } from "@/entities/user/model/keys";

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.detail,
    queryFn: () => profileApi.get().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => profileApi.update(data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: profileKeys.detail });
    },
  });
}
