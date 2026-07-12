import { useRouter } from "next/navigation";
import { getNotificationLink } from "@/lib/utils/notifications";

export function NotificationItem({ notification, onRead, compact = false, onAfterClick }) {
  const router = useRouter();

  const handleClick = () => {
    if (!notification.is_read) onRead(notification.id);
    const link = getNotificationLink(notification);
    if (link) router.push(link);
    onAfterClick?.();
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      className={`flex w-full flex-col gap-1 rounded-lg px-3 py-2 text-left transition-colors hover:bg-gray-100 dark:hover:bg-gray-800 ${
        compact ? "text-sm" : ""
      } ${!notification.is_read ? "bg-blue-50 dark:bg-blue-900/20" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium text-gray-900 dark:text-gray-100">
          {notification.title}
        </span>
        {!notification.is_read && (
          <span className="mt-1 h-2 w-2 shrink-0 rounded-full bg-blue-600" aria-label="Непрочитано" />
        )}
      </div>
      <p className="text-sm text-gray-600 dark:text-gray-400">{notification.body}</p>
      <span className="text-xs text-gray-400 dark:text-gray-500">
        {new Date(notification.created_at).toLocaleString("ru-RU", {
          dateStyle: "short",
          timeStyle: "short",
        })}
      </span>
    </button>
  );
}
