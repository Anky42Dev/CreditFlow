"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { applicationSchema } from "@/lib/validation/schemas";
import { useProducts, useProduct } from "@/hooks/useProducts";
import { useCreateApplication } from "@/hooks/useApplications";
import { calcAnnuity } from "@/lib/utils/annuity";
import { formatMoney } from "@/lib/utils/format";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";

export default function ApplicationForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedProduct = searchParams.get("product") || "";

  const { data: productsPage } = useProducts({ page_size: 100 });
  const products = productsPage?.results || [];

  const createApplication = useCreateApplication();

  const {
    register,
    handleSubmit,
    watch,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(applicationSchema),
    defaultValues: {
      product: preselectedProduct,
      amount: "",
      term_months: "",
      purpose: "",
    },
  });

  const [selectedProductId, setSelectedProductId] = useState(preselectedProduct);
  const watchedProduct = watch("product");
  const amount = watch("amount");
  const termMonths = watch("term_months");

  useEffect(() => {
    setSelectedProductId(watchedProduct);
  }, [watchedProduct]);

  const { data: selectedProduct } = useProduct(selectedProductId);

  const monthlyPayment =
    selectedProduct && amount && termMonths
      ? calcAnnuity(amount, selectedProduct.interest_rate, termMonths)
      : null;

  const onSubmit = async (values) => {
    try {
      const application = await createApplication.mutateAsync({
        product: values.product,
        amount: values.amount,
        term_months: values.term_months,
        purpose: values.purpose || "",
      });
      toast.success("Заявка создана");
      router.push(`/applications/${application.id}`);
    } catch (e) {
      const status = e.response?.status;
      const details = e.response?.data?.error?.details;
      if (status === 404) {
        setError("product", { message: "Продукт не найден" });
      } else if (details) {
        Object.entries(details).forEach(([field, messages]) => {
          setError(field, { message: Array.isArray(messages) ? messages[0] : messages });
        });
      } else {
        toast.error("Ошибка создания заявки");
      }
    }
  };

  return (
    <Card>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Продукт
          </label>
          <select
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
            {...register("product")}
          >
            <option value="">Выберите продукт</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.interest_rate}%)
              </option>
            ))}
          </select>
          {errors.product && (
            <span className="text-sm text-red-500">{errors.product.message}</span>
          )}
        </div>

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

        {selectedProduct && (
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Диапазон: {formatMoney(selectedProduct.min_amount)} – {formatMoney(selectedProduct.max_amount)},{" "}
            {selectedProduct.min_term_months}–{selectedProduct.max_term_months} мес.
          </p>
        )}
        {monthlyPayment != null && (
          <p className="text-sm font-medium text-gray-900 dark:text-gray-100">
            Ориентировочный платёж: {formatMoney(monthlyPayment)}/мес.
          </p>
        )}

        <Button type="submit" disabled={isSubmitting} className="w-full">
          Создать заявку
        </Button>
      </form>
    </Card>
  );
}
