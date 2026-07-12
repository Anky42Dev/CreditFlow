"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/entities/user/model/useAuth";
import { usePermission } from "@/entities/user/lib/usePermission";
import { useWSEvents } from "@/app/providers/useWSEvents";
import { PERMISSIONS } from "@/shared/config/permissions";
import { AdminSidebar } from "@/widgets/admin-sidebar/ui/AdminSidebar";
import { Header } from "@/widgets/header/ui/Header";
import { Loader } from "@/shared/ui/Loader";

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
