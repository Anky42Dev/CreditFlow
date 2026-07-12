"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { profileSchema } from "@/widgets/profile-form/model/schema";
import { useProfile, useUpdateProfile } from "@/entities/user/model/useProfile";
import { Input } from "@/shared/ui/Input";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { DetailSkeleton } from "@/shared/ui/Skeleton";
import { ErrorState } from "@/shared/ui/ErrorState";
import AvatarUpload from "@/features/avatar-upload/ui/AvatarUpload";

export default function ProfileForm() {
  const { data, isLoading, isError, refetch } = useProfile();
  const updateProfile = useUpdateProfile();

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    resolver: zodResolver(profileSchema),
    values: data
      ? {
          first_name: data.first_name || "",
          last_name: data.last_name || "",
          birth_date: data.birth_date || "",
          phone: data.phone || "",
          monthly_income: data.monthly_income ?? "",
        }
      : undefined,
  });

  const onSubmit = async (values) => {
    const payload = {
      ...values,
      birth_date: values.birth_date || null,
      monthly_income: values.monthly_income === "" ? null : values.monthly_income,
    };
    try {
      await updateProfile.mutateAsync(payload);
      toast.success("Профиль обновлён");
    } catch (e) {
      const details = e.response?.data?.error?.details;
      if (details) {
        Object.entries(details).forEach(([field, messages]) => {
          setError(field, { message: Array.isArray(messages) ? messages[0] : messages });
        });
      } else {
        toast.error("Ошибка обновления профиля");
      }
    }
  };

  if (isLoading) return <DetailSkeleton />;
  if (isError) {
    return <ErrorState description="Не удалось загрузить профиль" onRetry={refetch} />;
  }

  return (
    <div className="space-y-6">
      <Card>
        <AvatarUpload current={data?.avatar} />
      </Card>
      <Card>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Имя"
              error={errors.first_name?.message}
              {...register("first_name")}
            />
            <Input
              label="Фамилия"
              error={errors.last_name?.message}
              {...register("last_name")}
            />
            <Input
              label="Дата рождения"
              type="date"
              error={errors.birth_date?.message}
              {...register("birth_date")}
            />
            <Input
              label="Телефон"
              placeholder="+79991234567"
              error={errors.phone?.message}
              {...register("phone")}
            />
            <Input
              label="Ежемесячный доход"
              type="number"
              step="0.01"
              min="0"
              error={errors.monthly_income?.message}
              {...register("monthly_income")}
            />
          </div>
          <Button type="submit" disabled={isSubmitting}>
            Сохранить
          </Button>
        </form>
      </Card>
    </div>
  );
}
