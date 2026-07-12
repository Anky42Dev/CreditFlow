"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import toast from "react-hot-toast";
import { registerSchema } from "@/features/auth-by-credentials/model/schemas";
import { authApi } from "@/entities/user/api/auth";
import { Input } from "@/shared/ui/Input";
import { Button } from "@/shared/ui/Button";

export default function RegisterForm() {
  const router = useRouter();
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({ resolver: zodResolver(registerSchema) });

  const onSubmit = async (values) => {
    try {
      await authApi.register(values);
      toast.success("Регистрация успешна! Войдите.");
      router.push("/login");
    } catch (e) {
      const error = e.response?.data?.error;
      if (error?.code === "EMAIL_TAKEN") {
        setError("email", { message: "Email уже занят" });
        return;
      }
      const details = error?.details;
      if (details && typeof details === "object") {
        Object.entries(details).forEach(([field, messages]) => {
          setError(field, { message: [].concat(messages).join(" ") });
        });
      } else {
        toast.error(error?.message || "Ошибка регистрации");
      }
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input
        label="Email"
        type="email"
        placeholder="you@example.com"
        error={errors.email?.message}
        {...register("email")}
      />
      <Input
        label="Пароль"
        type="password"
        placeholder="••••••••"
        error={errors.password?.message}
        {...register("password")}
      />
      <Button type="submit" disabled={isSubmitting} className="w-full">
        Зарегистрироваться
      </Button>
      <p className="text-center text-sm text-gray-600 dark:text-gray-400">
        Уже есть аккаунт?{" "}
        <Link href="/login" className="text-blue-600 hover:underline">
          Войти
        </Link>
      </p>
    </form>
  );
}
