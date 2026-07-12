"use client";

import { useState } from "react";
import toast from "react-hot-toast";
import { useRequirePermission } from "@/hooks/useRequirePermission";
import { PERMISSIONS } from "@/lib/rbac/permissions";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { useAdminUsers, useChangeUserRole } from "@/hooks/useAdminUsers";
import { UsersTable } from "@/components/admin/UsersTable";
import { Input } from "@/components/ui/Input";
import { DetailSkeleton } from "@/components/feedback/Skeleton";

export default function AdminUsersPage() {
  const allowed = useRequirePermission(PERMISSIONS.USER_MANAGE);
  const [page, setPage] = useState(1);
  const [emailInput, setEmailInput] = useState("");
  const email = useDebouncedValue(emailInput);

  const { data, isLoading, isError, refetch } = useAdminUsers({ email: email || undefined, page });
  const changeRole = useChangeUserRole();

  if (!allowed) return <DetailSkeleton />;

  const onRoleChange = async (id, role) => {
    try {
      await changeRole.mutateAsync({ id, role });
      toast.success("Роль обновлена");
    } catch (e) {
      toast.error(e.response?.data?.error?.message || "Не удалось изменить роль");
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Пользователи</h1>
      <Input
        label="Поиск по email"
        value={emailInput}
        onChange={(e) => {
          setEmailInput(e.target.value);
          setPage(1);
        }}
        className="max-w-xs"
      />
      <UsersTable
        data={data}
        isLoading={isLoading}
        isError={isError}
        onRetry={refetch}
        page={page}
        onPageChange={setPage}
        onRoleChange={onRoleChange}
        changingId={changeRole.isPending ? changeRole.variables?.id : null}
      />
    </div>
  );
}
