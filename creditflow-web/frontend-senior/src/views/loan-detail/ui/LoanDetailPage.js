import { LoanDetail } from "@/widgets/loan-summary/ui/LoanSummary";
import { WidgetErrorBoundary } from "@/shared/lib/ErrorBoundary";

export function LoanDetailPage({ id }) {
  return (
    <WidgetErrorBoundary name="loan-detail">
      <LoanDetail id={id} />
    </WidgetErrorBoundary>
  );
}
