import { Input } from "@/shared/ui/Input";

export function AuditFilters({ filters, onFieldChange }) {
  return (
    <div className="flex flex-wrap items-end gap-4">
      <Input
        label="ID автора"
        type="number"
        value={filters.actor || ""}
        onChange={(e) => onFieldChange("actor", e.target.value || undefined)}
      />
      <Input
        label="Действие"
        placeholder="application.approved"
        value={filters.action || ""}
        onChange={(e) => onFieldChange("action", e.target.value || undefined)}
      />
      <Input
        label="Тип объекта"
        placeholder="CreditApplication"
        value={filters.object_type || ""}
        onChange={(e) => onFieldChange("object_type", e.target.value || undefined)}
      />
      <Input
        label="Дата с"
        type="datetime-local"
        value={filters.created_from || ""}
        onChange={(e) => onFieldChange("created_from", e.target.value || undefined)}
      />
      <Input
        label="Дата по"
        type="datetime-local"
        value={filters.created_to || ""}
        onChange={(e) => onFieldChange("created_to", e.target.value || undefined)}
      />
    </div>
  );
}
