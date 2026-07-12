import api from "@/shared/api/client";
import { toSearchParams } from "@/shared/lib/queryParams";

export const adminProductsApi = {
  list: (params) => api.get("/admin/credit-products", { params: toSearchParams(params) }),
  create: (data) => api.post("/admin/credit-products", data),
  update: (id, data) => api.put(`/admin/credit-products/${id}`, data),
  deactivate: (id) => api.delete(`/admin/credit-products/${id}`),
};
