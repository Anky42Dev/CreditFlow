import { LoanDetailPage } from "@/views/loan-detail/ui/LoanDetailPage";

export default async function Page({ params }) {
  const { id } = await params;
  return <LoanDetailPage id={id} />;
}
