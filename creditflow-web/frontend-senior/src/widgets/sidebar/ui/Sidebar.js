"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, User, FileText, Bell, ShieldCheck, X } from "lucide-react";
import { Can } from "@/entities/user/lib/Can";
import { PERMISSIONS } from "@/shared/config/permissions";

const LINKS = [
  { href: "/products", label: "Продукты", icon: LayoutGrid },
  { href: "/applications", label: "Заявки", icon: FileText },
  { href: "/notifications", label: "Уведомления", icon: Bell },
  { href: "/profile", label: "Профиль", icon: User },
];

export function Sidebar({ open = false, onClose }) {
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
          <span className="text-lg font-bold text-blue-600">CreditFlow</span>
          <button
            onClick={onClose}
            className="rounded-lg p-1 text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 md:hidden"
            aria-label="Закрыть меню"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="flex flex-col gap-1">
          {LINKS.map(({ href, label, icon: Icon }) => {
            const isActive = pathname.startsWith(href);
            return (
              <Link
                key={href}
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
            );
          })}
          <Can perm={PERMISSIONS.APP_VIEW_ALL}>
            <Link
              href="/admin/applications"
              onClick={onClose}
              className="mt-4 flex items-center gap-3 rounded-lg border-t border-gray-200 px-3 py-2 pt-5 text-sm font-medium text-gray-700 hover:bg-gray-100 dark:border-gray-800 dark:text-gray-300 dark:hover:bg-gray-800"
            >
              <ShieldCheck size={18} />
              Админ-панель
            </Link>
          </Can>
        </nav>
      </aside>
    </>
  );
}
