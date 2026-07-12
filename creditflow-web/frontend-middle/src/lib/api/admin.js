import api from "./client";
import { toSearchParams } from "@/lib/utils/queryParams";

export const adminProductsApi = {
  list: (params) => api.get("/admin/credit-products", { params: toSearchParams(params) }),
  create: (data) => api.post("/admin/credit-products", data),
  update: (id, data) => api.put(`/admin/credit-products/${id}`, data),
  deactivate: (id) => api.delete(`/admin/credit-products/${id}`),
};

export const adminApplicationsApi = {
  list: (params) => api.get("/admin/applications", { params: toSearchParams(params) }),
  get: (id) => api.get(`/admin/applications/${id}`),
  approve: (id, data) => api.post(`/admin/applications/${id}/approve`, data),
  reject: (id, data) => api.post(`/admin/applications/${id}/reject`, data),
  requestDocuments: (id) => api.post(`/admin/applications/${id}/request-documents`),
};

export const adminUsersApi = {
  list: (params) => api.get("/admin/users", { params: toSearchParams(params) }),
  changeRole: (id, role) => api.patch(`/admin/users/${id}/role`, { role }),
};

export const adminAuditApi = {
  list: (params) => api.get("/admin/audit-log", { params: toSearchParams(params) }),
};
