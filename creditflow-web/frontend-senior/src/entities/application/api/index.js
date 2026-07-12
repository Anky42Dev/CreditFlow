import api from "@/shared/api/client";

export const applicationsApi = {
  list: (params) => api.get("/credit-applications", { params }),
  get: (id) => api.get(`/credit-applications/${id}`),
  create: (data) => api.post("/credit-applications", data),
  update: (id, data) => api.put(`/credit-applications/${id}`, data),
  remove: (id) => api.delete(`/credit-applications/${id}`),
  submit: (id) => api.post(`/credit-applications/${id}/submit`),
};
