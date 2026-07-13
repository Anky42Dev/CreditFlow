"use client";

import { useState } from "react";
import { useLoans } from "@/entities/loan/model/useLoans";
import { LoanList } from "@/widgets/loan-list/ui/LoanList";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function LoansPage() {
  const [page, setPage] = useState(1);

  const { data, isLoading, isError, refetch } = useLoans({ page });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
        Мои договоры
      </h1>
      <WidgetErrorBoundary name="loan-list">
        <LoanList
          data={data}
          isLoading={isLoading}
          isError={isError}
          page={page}
          onPageChange={setPage}
          onRetry={refetch}
        />
      </WidgetErrorBoundary>
    </div>
  );
}
