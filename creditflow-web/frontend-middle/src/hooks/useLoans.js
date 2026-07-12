"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { loansApi } from "@/lib/api/loans";

export function useLoans(params) {
  return useQuery({
    queryKey: ["loans", params],
    queryFn: () => loansApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useLoan(id) {
  return useQuery({
    queryKey: ["loan", id],
    queryFn: () => loansApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

export function useRepayLoan(id) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data) => loansApi.repay(id, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["loans"] });
      qc.invalidateQueries({ queryKey: ["loan", id] });
    },
  });
}
