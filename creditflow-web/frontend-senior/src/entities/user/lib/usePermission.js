"use client";

import { useAuth } from "@/entities/user/model/useAuth";

export function usePermission(perm) {
  const { user } = useAuth();
  return user?.permissions?.includes(perm) ?? false;
}
