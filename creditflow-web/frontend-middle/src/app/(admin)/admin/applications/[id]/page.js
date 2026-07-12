import { AdminApplicationDetail } from "@/components/admin/AdminApplicationDetail";

export default async function AdminApplicationDetailPage({ params }) {
  const { id } = await params;
  return <AdminApplicationDetail id={id} />;
}
