import { AdminApplicationDetail } from "@/widgets/admin-application-detail/ui/AdminApplicationDetail";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function AdminApplicationDetailPage({ id }) {
  return (
    <WidgetErrorBoundary name="admin-application-detail">
      <AdminApplicationDetail id={id} />
    </WidgetErrorBoundary>
  );
}
