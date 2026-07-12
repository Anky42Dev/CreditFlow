import api from "@/shared/api/client";
import { toSearchParams } from "@/shared/lib/queryParams";

export const adminAuditApi = {
  list: (params) => api.get("/admin/audit-log", { params: toSearchParams(params) }),
};
