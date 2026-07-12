import api from "@/shared/api/client";
import { toSearchParams } from "@/shared/lib/queryParams";

export const adminApplicationsApi = {
  list: (params) => api.get("/admin/applications", { params: toSearchParams(params) }),
  get: (id) => api.get(`/admin/applications/${id}`),
  approve: (id, data) => api.post(`/admin/applications/${id}/approve`, data),
  reject: (id, data) => api.post(`/admin/applications/${id}/reject`, data),
  requestDocuments: (id) => api.post(`/admin/applications/${id}/request-documents`),
};
