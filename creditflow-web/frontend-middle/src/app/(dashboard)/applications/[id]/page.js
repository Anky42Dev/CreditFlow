import { ApplicationDetail } from "@/components/applications/ApplicationDetail";

export default async function ApplicationDetailPage({ params }) {
  const { id } = await params;
  return <ApplicationDetail id={id} />;
}
