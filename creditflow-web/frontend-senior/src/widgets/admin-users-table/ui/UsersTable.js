import { Badge } from "@/shared/ui/Badge";
import { AdminTable } from "@/widgets/admin-application-table/ui/AdminTable";
import { RoleSelect } from "@/entities/user/ui/RoleSelect";

const COLUMNS = [
  { key: "email", label: "Email" },
  { key: "role", label: "Роль" },
  { key: "status", label: "Статус" },
  { key: "created", label: "Создан" },
];

export function UsersTable({ data, isLoading, isError, onRetry, page, onPageChange, onRoleChange, changingId }) {
  return (
    <AdminTable
      columns={COLUMNS}
      data={data}
      isLoading={isLoading}
      isError={isError}
      onRetry={onRetry}
      page={page}
      onPageChange={onPageChange}
      emptyTitle="Пользователи не найдены"
      renderRow={(user) => (
        <tr key={user.id}>
          <td className="px-4 py-3 font-medium text-gray-900 dark:text-gray-100">{user.email}</td>
          <td className="px-4 py-3">
            <RoleSelect
              value={user.role}
              disabled={changingId === user.id}
              onChange={(role) => onRoleChange(user.id, role)}
            />
          </td>
          <td className="px-4 py-3">
            <Badge variant={user.is_active ? "green" : "gray"}>
              {user.is_active ? "Активен" : "Неактивен"}
            </Badge>
          </td>
          <td className="px-4 py-3 text-gray-500 dark:text-gray-400">
            {new Date(user.created_at).toLocaleDateString("ru-RU")}
          </td>
        </tr>
      )}
    />
  );
}
