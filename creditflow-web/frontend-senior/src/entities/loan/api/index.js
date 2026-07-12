import api from "@/shared/api/client";

export const loansApi = {
  list: (params) => api.get("/loans", { params }),
  get: (id) => api.get(`/loans/${id}`),
  repay: (id, data) => api.post(`/loans/${id}/repay`, data),
};
