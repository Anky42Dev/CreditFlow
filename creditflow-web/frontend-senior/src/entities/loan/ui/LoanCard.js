import Link from "next/link";
import { Card } from "@/shared/ui/Card";
import { LoanStatusBadge } from "./LoanStatusBadge";
import { formatMoney } from "@/shared/lib/format";
import { getNextPayment } from "@/entities/loan/lib/format";

export function LoanCard({ loan }) {
  const nextPayment = getNextPayment(loan);

  return (
    <Link href={`/loans/${loan.id}`}>
      <Card className="flex flex-col gap-2 transition-shadow hover:shadow-md">
        <div className="flex items-start justify-between gap-2">
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            Договор №{loan.id}
          </span>
          <LoanStatusBadge status={loan.status} />
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300">
          Остаток: {formatMoney(loan.outstanding_balance)}
        </div>
        {nextPayment && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            Ближайший платёж: {formatMoney(nextPayment.amount)} до{" "}
            {new Date(nextPayment.due_date).toLocaleDateString("ru-RU")}
          </div>
        )}
      </Card>
    </Link>
  );
}
