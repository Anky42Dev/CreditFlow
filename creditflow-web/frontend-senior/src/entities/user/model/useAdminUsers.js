"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { adminUsersApi } from "@/entities/user/api/admin";
import { adminUserKeys } from "@/entities/user/model/keys";

export function useAdminUsers(params) {
  return useQuery({
    queryKey: adminUserKeys.list(params),
    queryFn: () => adminUsersApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useChangeUserRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, role }) => adminUsersApi.changeRole(id, role).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: adminUserKeys.all });
    },
  });
}
