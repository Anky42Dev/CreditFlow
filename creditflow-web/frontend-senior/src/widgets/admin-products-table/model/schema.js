import { z } from "zod";

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
