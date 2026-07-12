import { Badge } from "@/components/ui/Badge";

const STATUS_MAP = {
  DRAFT: { label: "Черновик", variant: "gray" },
  SUBMITTED: { label: "Отправлена", variant: "blue" },
  SCORING: { label: "Скоринг", variant: "yellow" },
  APPROVED: { label: "Одобрена", variant: "green" },
  REJECTED: { label: "Отклонена", variant: "red" },
};

export function StatusBadge({ status }) {
  const { label, variant } = STATUS_MAP[status] || { label: status, variant: "gray" };
  return <Badge variant={variant}>{label}</Badge>;
}
