"use client";

import { useQuery, useMutation, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { adminProductsApi } from "@/lib/api/admin";

export function useAdminProducts(params) {
  return useQuery({
    queryKey: ["admin-products", params],
    queryFn: () => adminProductsApi.list(params).then((r) => r.data),
    staleTime: 30 * 1000,
    placeholderData: keepPreviousData,
  });
}

function useInvalidateAdminProducts() {
  const qc = useQueryClient();
  return () => {
    qc.invalidateQueries({ queryKey: ["admin-products"] });
    qc.invalidateQueries({ queryKey: ["products"] });
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
