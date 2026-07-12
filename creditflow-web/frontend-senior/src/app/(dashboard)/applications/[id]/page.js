import { ApplicationDetailPage } from "@/views/application-detail/ui/ApplicationDetailPage";

export default async function Page({ params }) {
  const { id } = await params;
  return <ApplicationDetailPage id={id} />;
}
