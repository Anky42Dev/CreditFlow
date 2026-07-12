export const notificationKeys = {
  all: ["notifications"],
  lists: () => [...notificationKeys.all, "list"],
  list: (filters) => [...notificationKeys.lists(), filters],
  unreadCount: ["unread-count"],
};
