"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { adminProductsApi } from "@/entities/product/api/admin";
import { adminProductKeys, productKeys } from "@/entities/product/model/keys";

export function useAdminProducts(params) {
  return useQuery({
    queryKey: adminProductKeys.list(params),
    queryFn: () => adminProductsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

function useInvalidateAdminProducts() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: adminProductKeys.all });
    qc.invalidateQueries({ queryKey: productKeys.all });
  };
}

export function useCreateAdminProduct() {
  const invalidate = useInvalidateAdminProducts();
  return useMutation({
    mutationFn: (data) => adminProductsApi.create(data).then((r) => r.data),
    onSuccess: invalidate,
  });
}

export function useUpdateAdminProduct(id) {
  const invalidate = useInvalidateAdminProducts();
  return useMutation({
    mutationFn: (data) => adminProductsApi.update(id, data).then((r) => r.data),
    onSuccess: invalidate,
  });
}

export function useDeactivateAdminProduct() {
  const invalidate = useInvalidateAdminProducts();
  return useMutation({
    mutationFn: (id) => adminProductsApi.deactivate(id),
    onSuccess: invalidate,
  });
}
