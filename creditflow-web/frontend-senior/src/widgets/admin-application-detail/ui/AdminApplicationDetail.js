"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import toast from "react-hot-toast";
import { useAdminApplication } from "@/entities/application/model/useAdminApplications";
import { useRequestDocuments } from "@/features/approve-application/model/useApproveApplication";
import { Can } from "@/entities/user/lib/Can";
import { PERMISSIONS } from "@/shared/config/permissions";
import { StatusBadge } from "@/entities/application/ui/StatusBadge";
import { Card } from "@/shared/ui/Card";
import { Button } from "@/shared/ui/Button";
import { DetailSkeleton } from "@/shared/ui/Skeleton";
import { ErrorState } from "@/shared/ui/ErrorState";
import { formatMoney } from "@/shared/lib/format";

const ApplicationDecisionModal = dynamic(
  () => import("@/features/approve-application/ui/ApplicationDecisionModal"),
  { loading: () => null, ssr: false }
);

export function AdminApplicationDetail({ id }) {
  const { data: application, isLoading, isError, error, refetch } = useAdminApplication(id);
  const requestDocuments = useRequestDocuments(id);
  const [decisionMode, setDecisionMode] = useState(null);

  if (isLoading) return <DetailSkeleton />;

  if (isError) {
    const notFound = error?.response?.status === 404;
    return (
      <ErrorState
        title={notFound ? "Заявка не найдена" : "Что-то пошло не так"}
        description={notFound ? undefined : "Не удалось загрузить заявку"}
        onRetry={notFound ? undefined : refetch}
      />
    );
  }

  const canDecide = application.status === "MANUAL_REVIEW";

  const onRequestDocuments = async () => {
    try {
      await requestDocuments.mutateAsync();
      toast.success("Запрос на документы отправлен клиенту");
    } catch {
      toast.error("Что-то пошло не так");
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Заявка №{application.id}
        </h1>
        <StatusBadge status={application.status} />
      </div>

      <Card className="space-y-4">
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Клиент</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {application.user_email}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Сумма</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {formatMoney(application.amount)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Срок</dt>
            <dd className="font-medium text-gray-900 dark:text-gray-100">
              {application.term_months} мес.
            </dd>
          </div>
          {application.monthly_payment && (
            <div>
              <dt className="text-gray-500 dark:text-gray-400">Платёж</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {formatMoney(application.monthly_payment)}/мес.
              </dd>
            </div>
          )}
          {application.purpose && (
            <div className="col-span-2">
              <dt className="text-gray-500 dark:text-gray-400">Цель</dt>
              <dd className="font-medium text-gray-900 dark:text-gray-100">
                {application.purpose}
              </dd>
            </div>
          )}
        </dl>

        {application.scoring_result && (
          <div className="rounded-lg bg-gray-50 p-3 text-sm dark:bg-gray-800">
            <p className="font-medium text-gray-900 dark:text-gray-100">
              Скоринг: {application.scoring_result.score} баллов (
              {application.scoring_result.decision})
            </p>
            <p className="text-gray-600 dark:text-gray-400">{application.scoring_result.reason}</p>
          </div>
        )}

        {application.documents?.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-gray-900 dark:text-gray-100">Документы</p>
            <ul className="space-y-1 text-sm">
              {application.documents.map((doc) => (
                <li key={doc.id}>
                  <a
                    href={doc.file}
                    target="_blank"
                    rel="noreferrer"
                    className="text-blue-600 hover:underline dark:text-blue-400"
                  >
                    {doc.doc_type}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="flex flex-wrap gap-3">
          {canDecide && (
            <Can perm={PERMISSIONS.APP_APPROVE}>
              <Button onClick={() => setDecisionMode("approve")}>Одобрить</Button>
            </Can>
          )}
          {canDecide && (
            <Can perm={PERMISSIONS.APP_REJECT}>
              <Button variant="danger" onClick={() => setDecisionMode("reject")}>
                Отклонить
              </Button>
            </Can>
          )}
          <Button
            variant="secondary"
            disabled={requestDocuments.isPending}
            onClick={onRequestDocuments}
          >
            Запросить документы
          </Button>
        </div>
      </Card>

      {decisionMode && (
        <ApplicationDecisionModal
          open={Boolean(decisionMode)}
          onClose={() => setDecisionMode(null)}
          applicationId={id}
          mode={decisionMode}
        />
      )}
    </div>
  );
}
