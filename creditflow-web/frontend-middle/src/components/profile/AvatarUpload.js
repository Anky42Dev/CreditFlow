"use client";

import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { profileApi } from "@/lib/api/profile";

const MAX_SIZE = 2 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png"];

export default function AvatarUpload({ current }) {
  const [preview, setPreview] = useState(current || null);
  const [isUploading, setUploading] = useState(false);
  const qc = useQueryClient();

  const onChange = async (e) => {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;

    if (file.size > MAX_SIZE) {
      toast.error("Файл больше 2 МБ");
      return;
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      toast.error("Только JPEG/PNG");
      return;
    }

    const objectUrl = URL.createObjectURL(file);
    setPreview(objectUrl);
    setUploading(true);
    try {
      const { data } = await profileApi.uploadAvatar(file);
      setPreview(data.avatar);
      qc.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Аватар обновлён");
    } catch {
      toast.error("Ошибка загрузки аватара");
    } finally {
      URL.revokeObjectURL(objectUrl);
      setUploading(false);
    }
  };

  return (
    <div className="flex items-center gap-4">
      {preview ? (
        <img
          src={preview}
          alt="Аватар"
          className="h-24 w-24 rounded-full object-cover"
        />
      ) : (
        <div className="flex h-24 w-24 items-center justify-center rounded-full bg-gray-200 text-sm text-gray-500 dark:bg-gray-800 dark:text-gray-400">
          Нет фото
        </div>
      )}
      <div className="space-y-1">
        <label className="inline-flex cursor-pointer items-center rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-900 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-100 dark:hover:bg-gray-700">
          {isUploading ? "Загрузка..." : "Загрузить фото"}
          <input
            type="file"
            accept="image/jpeg,image/png"
            className="hidden"
            disabled={isUploading}
            onChange={onChange}
          />
        </label>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          JPEG или PNG, до 2 МБ
        </p>
      </div>
    </div>
  );
}
