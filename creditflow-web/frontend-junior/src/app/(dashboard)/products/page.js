"use client";

import { useState } from "react";
import { useProducts } from "@/hooks/useProducts";
import { ProductFilters } from "@/components/products/ProductFilters";
import { ProductList } from "@/components/products/ProductList";

export default function ProductsPage() {
  const [search, setSearch] = useState("");
  const [ordering, setOrdering] = useState("-created_at");
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useProducts({ search, ordering, page });

  const handleSearchChange = (value) => {
    setSearch(value);
    setPage(1);
  };

  const handleOrderingChange = (value) => {
    setOrdering(value);
    setPage(1);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Кредитные продукты
      </h1>
      <ProductFilters
        search={search}
        ordering={ordering}
        onSearchChange={handleSearchChange}
        onOrderingChange={handleOrderingChange}
      />
      <ProductList
        data={data}
        isLoading={isLoading}
        isError={isError}
        page={page}
        onPageChange={setPage}
        onRetry={refetch}
      />
    </div>
  );
}
