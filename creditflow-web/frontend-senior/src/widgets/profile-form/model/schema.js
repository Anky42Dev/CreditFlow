import { z } from "zod";

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
