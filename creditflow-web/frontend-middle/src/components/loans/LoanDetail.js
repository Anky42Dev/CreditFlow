"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { useLoan } from "@/hooks/useLoans";
import { getNextPayment } from "@/lib/utils/loans";
import { formatMoney, formatRate } from "@/lib/utils/format";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DetailSkeleton } from "@/components/feedback/Skeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { LoanStatusBadge } from "./LoanStatusBadge";
import { ScheduleTable } from "./ScheduleTable";

const RepayModal = dynamic(() => import("./RepayModal").then((mod) => mod.RepayModal), {
  loading: () => null,
  ssr: false,
});

export function LoanDetail({ id }) {
  const { data: loan, isLoading, isError, error, refetch } = useLoan(id);
  const [repayOpen, setRepayOpen] = useState(false);

  if (isLoading) return <DetailSkeleton />;

  if (isError) {
    const notFound = error?.response?.status === 404;
    return (
      <ErrorState
        title={notFound ? "Договор не найден" : "Что-то пошло не так"}
        description={notFound ? undefined : "Не удалось загрузить договор"}
        onRetry={notFound ? undefined : refetch}
      />
    );
  }

  const nextPayment = getNextPayment(loan);

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Договор №{loan.id}
        </h1>
        <LoanStatusBadge status={loan.status} />
      </div>

      <Card className="space-y-4">
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Сумма кредита</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatMoney(loan.principal)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Остаток</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatMoney(loan.outstanding_balance)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Ставка</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatRate(loan.interest_rate)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Платёж</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatMoney(loan.monthly_payment)}/мес.
            </dd>
          </div>
        </dl>

        {nextPayment && loan.status !== "CLOSED" && (
          <div className="flex items-center justify-between rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-800">
            <span className="text-gray-700 dark:text-gray-300">
              Ближайший платёж: {formatMoney(nextPayment.amount)} до{" "}
              {new Date(nextPayment.due_date).toLocaleDateString("ru-RU")}
            </span>
            <Button onClick={() => setRepayOpen(true)}>Внести платёж</Button>
          </div>
        )}
      </Card>

      <Card>
        <h2 className="mb-3 text-lg font-semibold text-gray-900 dark:text-gray-100">
          График платежей
        </h2>
        <ScheduleTable items={loan.schedule_items} />
      </Card>

      {repayOpen && (
        <RepayModal
          open={repayOpen}
          onClose={() => setRepayOpen(false)}
          loanId={id}
          nextPayment={nextPayment}
        />
      )}
    </div>
  );
}
