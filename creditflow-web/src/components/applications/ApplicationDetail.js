"use client";

import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { applicationUpdateSchema } from "@/lib/validation/schemas";
import {
  useApplication,
  useUpdateApplication,
  useSubmitApplication,
  useDeleteApplication,
} from "@/hooks/useApplications";
import { useProduct } from "@/hooks/useProducts";
import { calcAnnuity } from "@/lib/utils/annuity";
import { formatMoney } from "@/lib/utils/format";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { DetailSkeleton } from "@/components/feedback/Skeleton";
import { ErrorState } from "@/components/feedback/ErrorState";
import { StatusBadge } from "./StatusBadge";

export function ApplicationDetail({ id }) {
  const router = useRouter();
  const { data: application, isLoading, isError, error, refetch } = useApplication(id);
  const { data: product } = useProduct(application?.product);

  const updateApplication = useUpdateApplication(id);
  const submitApplication = useSubmitApplication(id);
  const deleteApplication = useDeleteApplication(id);

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(applicationUpdateSchema),
    values: application
      ? {
          amount: application.amount,
          term_months: application.term_months,
          purpose: application.purpose || "",
        }
      : undefined,
  });

  const amount = watch("amount");
  const termMonths = watch("term_months");
  const monthlyPayment =
    product && amount && termMonths ? calcAnnuity(amount, product.interest_rate, termMonths) : null;

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

  const mapErrorDetails = (e) => {
    const status = e.response?.status;
    const details = e.response?.data?.error?.details;
    if (status === 409) {
      toast.error(e.response?.data?.error?.message || "Действие недоступно в этом статусе");
    } else if (details) {
      Object.entries(details).forEach(([field, messages]) => {
        setError(field, { message: Array.isArray(messages) ? messages[0] : messages });
      });
    } else {
      toast.error("Что-то пошло не так");
    }
  };

  const onSave = async (values) => {
    try {
      await updateApplication.mutateAsync({
        amount: values.amount,
        term_months: values.term_months,
        purpose: values.purpose || "",
      });
      toast.success("Заявка обновлена");
    } catch (e) {
      mapErrorDetails(e);
    }
  };

  const onSubmitApplication = async () => {
    try {
      await submitApplication.mutateAsync();
      toast.success("Заявка отправлена");
    } catch (e) {
      mapErrorDetails(e);
    }
  };

  const onDelete = async () => {
    if (!window.confirm("Удалить заявку?")) return;
    try {
      await deleteApplication.mutateAsync();
      toast.success("Заявка удалена");
      router.push("/applications");
    } catch (e) {
      mapErrorDetails(e);
    }
  };

  const isDraft = application.status === "DRAFT";

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
          Заявка №{application.id}
        </h1>
        <StatusBadge status={application.status} />
      </div>

      {isDraft ? (
        <Card>
          <form onSubmit={handleSubmit(onSave)} className="space-y-4">
            {product && (
              <p className="text-sm text-gray-600 dark:text-gray-400">
                Продукт: {product.name} ({product.interest_rate}%)
              </p>
            )}
            <Input
              label="Сумма"
              type="number"
              step="0.01"
              min="0"
              error={errors.amount?.message}
              {...register("amount")}
            />
            <Input
              label="Срок (мес.)"
              type="number"
              min="1"
              error={errors.term_months?.message}
              {...register("term_months")}
            />
            <Input
              label="Цель (необязательно)"
              error={errors.purpose?.message}
              {...register("purpose")}
            />
            {monthlyPayment != null && (
              <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
                Ориентировочный платёж: {formatMoney(monthlyPayment)}/мес.
              </p>
            )}
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={isSubmitting}>
                Сохранить
              </Button>
              <Button
                type="button"
                variant="secondary"
                disabled={submitApplication.isPending}
                onClick={onSubmitApplication}
              >
                Отправить
              </Button>
              <Button
                type="button"
                variant="danger"
                disabled={deleteApplication.isPending}
                onClick={onDelete}
              >
                Удалить
              </Button>
            </div>
          </form>
        </Card>
      ) : (
        <Card className="space-y-4">
          {product && (
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Продукт: {product.name} ({product.interest_rate}%)
            </p>
          )}
          <dl className="grid grid-cols-2 gap-4 text-sm">
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
              <div>
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
                Скоринг: {application.scoring_result.score} баллов
              </p>
              <p className="text-gray-600 dark:text-gray-400">
                {application.scoring_result.reason}
              </p>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
