"use client";

import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { adminProductSchema } from "@/lib/validation/schemas";
import { useCreateAdminProduct, useUpdateAdminProduct } from "@/hooks/useAdminProducts";
import { Modal } from "@/components/ui/Modal";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";

const EMPTY_VALUES = {
  name: "",
  slug: "",
  description: "",
  min_amount: "",
  max_amount: "",
  interest_rate: "",
  min_term_months: "",
  max_term_months: "",
};

export default function ProductFormModal({ open, onClose, product }) {
  const isEdit = Boolean(product);
  const createProduct = useCreateAdminProduct();
  const updateProduct = useUpdateAdminProduct(product?.id);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(adminProductSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    reset(product ? { ...EMPTY_VALUES, ...product } : EMPTY_VALUES);
  }, [open, product, reset]);

  const onSubmit = async (values) => {
    try {
      if (isEdit) {
        await updateProduct.mutateAsync({ ...values, is_active: product.is_active });
        toast.success("Продукт обновлён");
      } else {
        await createProduct.mutateAsync(values);
        toast.success("Продукт создан");
      }
      onClose();
    } catch (e) {
      const details = e.response?.data?.error?.details;
      if (details) {
        Object.entries(details).forEach(([field, messages]) => {
          setError(field, { message: Array.isArray(messages) ? messages[0] : messages });
        });
      } else {
        toast.error(e.response?.data?.error?.message || "Что-то пошло не так");
      }
    }
  };

  const isPending = createProduct.isPending || updateProduct.isPending;

  return (
    <Modal open={open} onClose={onClose} title={isEdit ? "Редактировать продукт" : "Новый продукт"}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input label="Название" error={errors.name?.message} {...register("name")} />
        <Input label="Slug" error={errors.slug?.message} {...register("slug")} />
        <Input label="Описание" error={errors.description?.message} {...register("description")} />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Мин. сумма"
            type="number"
            step="0.01"
            error={errors.min_amount?.message}
            {...register("min_amount")}
          />
          <Input
            label="Макс. сумма"
            type="number"
            step="0.01"
            error={errors.max_amount?.message}
            {...register("max_amount")}
          />
          <Input
            label="Ставка, %"
            type="number"
            step="0.01"
            error={errors.interest_rate?.message}
            {...register("interest_rate")}
          />
          <Input
            label="Мин. срок, мес."
            type="number"
            error={errors.min_term_months?.message}
            {...register("min_term_months")}
          />
          <Input
            label="Макс. срок, мес."
            type="number"
            error={errors.max_term_months?.message}
            {...register("max_term_months")}
          />
        </div>
        <div className="flex justify-end gap-3">
          <Button type="button" variant="secondary" onClick={onClose}>
            Отмена
          </Button>
          <Button type="submit" disabled={isPending || isSubmitting}>
            Сохранить
          </Button>
        </div>
      </form>
    </Modal>
  );
}
