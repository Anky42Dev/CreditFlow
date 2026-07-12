"use client";

import { useContext } from "react";
import { AuthContext } from "@/lib/auth/AuthContext";

export function useAuth() {
  return useContext(AuthContext);
}
