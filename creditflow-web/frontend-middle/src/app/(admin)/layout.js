"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { usePermission } from "@/hooks/usePermission";
import { useWSEvents } from "@/hooks/useWebSocket";
import { PERMISSIONS } from "@/lib/rbac/permissions";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { Header } from "@/components/layout/Header";
import { Loader } from "@/components/feedback/Loader";

export default function AdminLayout({ children }) {
  const { user, isLoading } = useAuth();
  const canAccess = usePermission(PERMISSIONS.APP_VIEW_ALL);
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useWSEvents();

  useEffect(() => {
    if (isLoading) return;
    if (!user) {
      router.replace("/login");
      return;
    }
    if (!canAccess) router.replace("/applications");
  }, [user, isLoading, canAccess, router]);

  if (isLoading || !user || !canAccess) return <Loader fullscreen />;

  return (
    <div className="flex min-h-screen">
      <AdminSidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
