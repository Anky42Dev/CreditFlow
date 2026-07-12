"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { applicationsApi } from "@/entities/application/api";
import { applicationKeys } from "@/entities/application/model/keys";

export function useSubmitApplication(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => applicationsApi.submit(id).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: applicationKeys.all });
      qc.invalidateQueries({ queryKey: applicationKeys.detail(id) });
    },
  });
}
