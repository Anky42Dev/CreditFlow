import { Badge } from "@/components/ui/Badge";

const STATUS_MAP = {
  ACTIVE: { label: "Активен", variant: "blue" },
  OVERDUE: { label: "Просрочен", variant: "red" },
  CLOSED: { label: "Закрыт", variant: "gray" },
};

export function LoanStatusBadge({ status }) {
  const { label, variant } = STATUS_MAP[status] || { label: status, variant: "gray" };
  return <Badge variant={variant}>{label}</Badge>;
}
