import axios from "axios";
import { getAccess, setAccess, clearAccess } from "@/shared/api/authStore";
import { decodeJwtExp } from "@/shared/lib/decodeJwt";
import { getCsrfToken } from "@/shared/lib/csrf";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL + "/api/v1",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const access = getAccess();
  if (access) config.headers.Authorization = `Bearer ${access}`;
  return config;
});

let isRefreshing = false;
let queue = [];

// DOC 6 §3.2/3.3: refresh cookie is sent automatically (withCredentials);
// the CSRF double-submit header protects this cookie-driven call.
export async function refreshAccessToken() {
  const csrfToken = getCsrfToken();
  const { data } = await axios.post(
    `${process.env.NEXT_PUBLIC_API_URL}/api/v1/auth/refresh`,
    {},
    {
      withCredentials: true,
      headers: csrfToken ? { "X-CSRFToken": csrfToken } : undefined,
    }
  );
  setAccess(data.access, decodeJwtExp(data.access));
  return data.access;
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const status = error.response?.status;
    const isRefreshCall = original?.url?.includes("/auth/refresh");

    if (status === 401 && !original._retry && !isRefreshCall) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          queue.push({ resolve, reject, original });
        });
      }
      isRefreshing = true;
      try {
        const access = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${access}`;
        queue.forEach((p) => {
          p.original.headers.Authorization = `Bearer ${access}`;
          p.resolve(api(p.original));
        });
        queue = [];
        return api(original);
      } catch (e) {
        queue.forEach((p) => p.reject(e));
        queue = [];
        clearAccess();
        window.location.href = "/login";
        return Promise.reject(e);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

export default api;
