import Link from "next/link";
import { Card } from "@/components/ui/Card";
import { StatusBadge } from "./StatusBadge";
import { formatMoney } from "@/lib/utils/format";

export function ApplicationCard({ application }) {
  return (
    <Link href={`/applications/${application.id}`}>
      <Card className="flex flex-col gap-2 transition-shadow hover:shadow-md">
        <div className="flex items-start justify-between gap-2">
          <span className="font-semibold text-gray-900 dark:text-gray-100">
            Заявка №{application.id}
          </span>
          <StatusBadge status={application.status} />
        </div>
        <div className="text-sm text-gray-700 dark:text-gray-300">
          {formatMoney(application.amount)} на {application.term_months} мес.
        </div>
        {application.purpose && (
          <div className="text-sm text-gray-500 dark:text-gray-400">
            {application.purpose}
          </div>
        )}
        <div className="text-xs text-gray-400 dark:text-gray-500">
          {new Date(application.created_at).toLocaleDateString("ru-RU")}
        </div>
      </Card>
    </Link>
  );
}
