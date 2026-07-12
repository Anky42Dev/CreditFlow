"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { loansApi } from "@/entities/loan/api";
import { loanKeys } from "@/entities/loan/model/keys";

export function useRepayLoan(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => loansApi.repay(id, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: loanKeys.all });
      qc.invalidateQueries({ queryKey: loanKeys.detail(id) });
    },
  });
}
