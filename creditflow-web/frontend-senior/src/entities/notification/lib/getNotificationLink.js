const TARGET_BY_TYPE_PREFIX = [
  { prefix: "application.", base: "/applications" },
  { prefix: "loan.", base: "/loans" },
  { prefix: "payment.", base: "/loans" },
];

// Backend embeds the related object id as "№{id}" in the notification body
// (apps/notifications/services.py render_body) — there is no dedicated id field.
export function getNotificationLink(notification) {
  const match = notification?.body?.match(/№(\d+)/);
  if (!match) return null;

  const target = TARGET_BY_TYPE_PREFIX.find(({ prefix }) =>
    notification.type?.startsWith(prefix)
  );
  if (!target) return null;

  return `${target.base}/${match[1]}`;
}
