"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { loansApi } from "@/entities/loan/api";
import { loanKeys } from "@/entities/loan/model/keys";

export function useLoans(params) {
  return useQuery({
    queryKey: loanKeys.list(params),
    queryFn: () => loansApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useLoan(id) {
  return useQuery({
    queryKey: loanKeys.detail(id),
    queryFn: () => loansApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}
