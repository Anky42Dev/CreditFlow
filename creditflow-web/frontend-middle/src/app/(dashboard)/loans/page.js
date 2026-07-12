"use client";

import { useState } from "react";
import { useLoans } from "@/hooks/useLoans";
import { LoanList } from "@/components/loans/LoanList";

export default function LoansPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useLoans({ page });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Мои договоры
      </h1>
      <LoanList
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
