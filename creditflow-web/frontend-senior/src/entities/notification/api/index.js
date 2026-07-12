import api from "@/shared/api/client";

export const notificationsApi = {
  list: (params) => api.get("/notifications", { params }),
  unreadCount: () => api.get("/notifications/unread-count"),
  read: (id) => api.post(`/notifications/${id}/read`),
  readAll: () => api.post("/notifications/read-all"),
};
