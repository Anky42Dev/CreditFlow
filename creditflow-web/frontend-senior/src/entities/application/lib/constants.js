export const ADMIN_STATUS_OPTIONS = [
  { value: "DRAFT", label: "Черновик" },
  { value: "SUBMITTED", label: "Отправлена" },
  { value: "SCORING", label: "Скоринг" },
  { value: "MANUAL_REVIEW", label: "Ручная проверка" },
  { value: "APPROVED", label: "Одобрена" },
  { value: "REJECTED", label: "Отклонена" },
  { value: "DISBURSED", label: "Выдана" },
];

/** Elapsed time since `dateStr`, for the MANUAL_REVIEW queue's waiting-time column. */
export function formatWaitTime(dateStr) {
  if (!dateStr) return "—";
  const diffMs = Date.now() - new Date(dateStr).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 60) return `${minutes} мин`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} ч`;
  const days = Math.floor(hours / 24);
  return `${days} дн`;
}
