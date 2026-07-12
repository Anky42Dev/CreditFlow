import api from "@/shared/api/client";
import { toSearchParams } from "@/shared/lib/queryParams";

export const adminUsersApi = {
  list: (params) => api.get("/admin/users", { params: toSearchParams(params) }),
  changeRole: (id, role) => api.patch(`/admin/users/${id}/role`, { role }),
};
