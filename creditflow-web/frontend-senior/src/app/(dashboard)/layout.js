"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/entities/user/model/useAuth";
import { useWSEvents } from "@/app/providers/useWSEvents";
import { Sidebar } from "@/widgets/sidebar/ui/Sidebar";
import { Header } from "@/widgets/header/ui/Header";
import { Loader } from "@/shared/ui/Loader";

export default function DashboardLayout({ children }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useWSEvents();

  useEffect(() => {
    if (!isLoading && !user) router.replace("/login");
  }, [user, isLoading, router]);

  if (isLoading) return <Loader fullscreen />;
  if (!user) return null;

  return (
    <div className="flex min-h-screen">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />
      <div className="flex flex-1 flex-col">
        <Header onMenuClick={() => setSidebarOpen(true)} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
