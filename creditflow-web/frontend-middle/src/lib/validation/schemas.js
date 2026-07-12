import { z } from "zod";

export const registerSchema = z.object({
  email: z.string().email("Некорректный email"),
  password: z
    .string()
    .min(8, "Минимум 8 символов")
    .regex(/[a-zA-Z]/, "Должна быть буква"),
});

export const loginSchema = z.object({
  email: z.string().email("Некорректный email"),
  password: z.string().min(1, "Введите пароль"),
});

export const profileSchema = z.object({
  first_name: z.string().max(50, "Максимум 50 символов").optional().or(z.literal("")),
  last_name: z.string().max(50, "Максимум 50 символов").optional().or(z.literal("")),
  birth_date: z.string().optional().or(z.literal("")),
  phone: z
    .string()
    .regex(/^\+?\d{7,15}$/, "Некорректный формат телефона")
    .optional()
    .or(z.literal("")),
  monthly_income: z.union([z.coerce.number().min(0, "Должно быть больше или равно 0"), z.literal("")]).optional(),
});

export const applicationSchema = z.object({
  product: z.coerce.number().int().positive("Выберите продукт"),
  amount: z.coerce.number().positive("Сумма должна быть > 0"),
  term_months: z.coerce.number().int().min(1, "Минимум 1 месяц"),
  purpose: z.string().max(255, "Максимум 255 символов").optional().or(z.literal("")),
});

export const applicationUpdateSchema = z.object({
  amount: z.coerce.number().positive("Сумма должна быть > 0"),
  term_months: z.coerce.number().int().min(1, "Минимум 1 месяц"),
  purpose: z.string().max(255, "Максимум 255 символов").optional().or(z.literal("")),
});

export const adminProductSchema = z
  .object({
    name: z.string().min(1, "Обязательное поле").max(120, "Максимум 120 символов"),
    slug: z
      .string()
      .min(1, "Обязательное поле")
      .max(120, "Максимум 120 символов")
      .regex(/^[a-z0-9-]+$/, "Строчные латинские буквы, цифры и дефис"),
    description: z.string().max(2000, "Максимум 2000 символов").optional().or(z.literal("")),
    min_amount: z.coerce.number().positive("Должно быть > 0"),
    max_amount: z.coerce.number().positive("Должно быть > 0"),
    interest_rate: z.coerce.number().min(0, "От 0 до 100").max(100, "От 0 до 100"),
    min_term_months: z.coerce.number().int().min(1, "Минимум 1"),
    max_term_months: z.coerce.number().int().min(1, "Минимум 1"),
  })
  .refine((data) => data.max_amount >= data.min_amount, {
    message: "Должна быть ≥ минимальной суммы",
    path: ["max_amount"],
  })
  .refine((data) => data.max_term_months >= data.min_term_months, {
    message: "Должен быть ≥ минимального срока",
    path: ["max_term_months"],
  });
