import api from "./client";

export const productsApi = {
  list: (params) => api.get("/credit-products", { params }),
  get: (id) => api.get(`/credit-products/${id}`),
};
