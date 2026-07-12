"use client";

import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { productsApi } from "@/lib/api/products";

export function useProducts(params) {
  return useQuery({
    queryKey: ["products", params],
    queryFn: () => productsApi.list(params).then((r) => r.data),
    staleTime: 5 * 60 * 1000,
    placeholderData: keepPreviousData,
  });
}

export function useProduct(id) {
  return useQuery({
    queryKey: ["product", id],
    queryFn: () => productsApi.get(id).then((r) => r.data),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });
}
