"use client";

import { useAuth } from "./useAuth";

export function usePermission(perm) {
  const { user } = useAuth();
  return user?.permissions?.includes(perm) ?? false;
}
