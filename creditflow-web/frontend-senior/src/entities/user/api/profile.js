import api from "@/shared/api/client";

export const profileApi = {
  get: () => api.get("/profile"),
  update: (data) => api.put("/profile", data),
  uploadAvatar: (file) => {
    const fd = new FormData();
    fd.append("avatar", file);
    return api.post("/profile/avatar", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
};
