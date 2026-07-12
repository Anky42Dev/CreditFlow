"use client";

import { createContext, useState, useEffect } from "react";
import { authApi } from "@/lib/api/auth";
import { getTokens, setTokens, clearTokens } from "./tokenStorage";

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setLoading] = useState(true);

  useEffect(() => {
    const { access } = getTokens();
    if (!access) {
      Promise.resolve().then(() => setLoading(false));
      return;
    }
    authApi
      .me()
      .then((r) => setUser(r.data))
      .catch(() => clearTokens())
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    const { data } = await authApi.login({ email, password });
    setTokens({ access: data.access, refresh: data.refresh });
    const me = await authApi.me();
    setUser(me.data);
  };

  const logout = () => {
    clearTokens();
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
