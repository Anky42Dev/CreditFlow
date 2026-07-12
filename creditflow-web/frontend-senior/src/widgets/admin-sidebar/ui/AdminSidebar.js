"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Package, FileText, Users, History, ArrowLeft, X } from "lucide-react";
import { Can } from "@/entities/user/lib/Can";
import { PERMISSIONS } from "@/shared/config/permissions";

const LINKS = [
  { href: "/admin/products", label: "Продукты", icon: Package, perm: PERMISSIONS.PRODUCT_MANAGE },
  { href: "/admin/applications", label: "Заявки", icon: FileText, perm: PERMISSIONS.APP_VIEW_ALL },
  { href: "/admin/users", label: "Пользователи", icon: Users, perm: PERMISSIONS.USER_MANAGE },
  { href: "/admin/audit", label: "Аудит", icon: History, perm: PERMISSIONS.AUDIT_VIEW },
];

export function AdminSidebar({ open = false, onClose }) {
  const pathname = usePathname();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 shrink-0 border-r border-gray-200 bg-white p-4 transition-transform dark:border-gray-800 dark:bg-gray-900 md:static md:translate-x-0 ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center justify-between">
          <span className="text-lg font-bold text-blue-600">CreditFlow Admin</span>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
            aria-label="Закрыть меню"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="flex flex-col gap-1">
          {LINKS.map(({ href, label, icon: Icon, perm }) => {
            const isActive = pathname.startsWith(href);
            return (
              <Can key={href} perm={perm}>
                <Link
                  href={href}
                  onClick={onClose}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                      : "text-gray-700 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
                  }`}
                >
                  <Icon size={18} />
                  {label}
                </Link>
              </Can>
            );
          })}
          <Link
            href="/applications"
            className="mt-4 flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            <ArrowLeft size={18} />
            Обычный кабинет
          </Link>
        </nav>
      </aside>
    </>
  );
}
