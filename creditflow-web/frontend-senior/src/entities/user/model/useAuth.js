"use client";

import { useContext } from "react";
import { AuthContext } from "@/entities/user/model/AuthContext";

export function useAuth() {
  return useContext(AuthContext);
}
