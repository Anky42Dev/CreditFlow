import { z } from "zod";

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
