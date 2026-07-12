import { AdminApplicationDetailPage } from "@/views/admin-application-detail/ui/AdminApplicationDetailPage";

export default async function Page({ params }) {
  const { id } = await params;
  return <AdminApplicationDetailPage id={id} />;
}
