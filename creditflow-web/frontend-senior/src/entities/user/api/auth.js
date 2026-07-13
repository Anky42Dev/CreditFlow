import api from "@/shared/api/client";
import { getCsrfToken } from "@/shared/lib/csrf";

export const authApi = {
  register: (data) => api.post("/auth/register", data),
  login: (data) => api.post("/auth/login", data),
  me: () => api.get("/auth/me"),
  logout: () =>
    api.post(
      "/auth/logout",
      {},
      { headers: { "X-CSRFToken": getCsrfToken() } }
    ),
};
