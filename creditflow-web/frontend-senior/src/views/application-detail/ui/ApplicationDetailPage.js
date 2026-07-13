import { ApplicationDetail } from "@/widgets/application-detail/ui/ApplicationDetail";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function ApplicationDetailPage({ id }) {
  return (
    <WidgetErrorBoundary name="application-detail">
      <ApplicationDetail id={id} />
    </WidgetErrorBoundary>
  );
}
