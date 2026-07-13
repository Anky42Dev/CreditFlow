"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { authApi } from "@/entities/user/api/auth";
import { refreshAccessToken } from "@/shared/api/client";
import { setAccess, clearAccess, getAccessExp } from "@/shared/api/authStore";
import { decodeJwtExp } from "@/shared/lib/decodeJwt";
import { AuthContext } from "@/entities/user/model/AuthContext";

const REFRESH_MARGIN_MS = 60_000; // silent refresh ~1 min before access expires

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setLoading] = useState(true);
  const timerRef = useRef(null);
  const scheduleRef = useRef(() => {});

  const scheduleSilentRefresh = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    const exp = getAccessExp();
    if (!exp) return;
    const ms = exp * 1000 - Date.now() - REFRESH_MARGIN_MS;
    timerRef.current = setTimeout(async () => {
      try {
        await refreshAccessToken();
        scheduleRef.current();
      } catch {
        clearAccess();
        setUser(null);
      }
    }, Math.max(ms, 0));
  }, []);

  useEffect(() => {
    scheduleRef.current = scheduleSilentRefresh;
  }, [scheduleSilentRefresh]);

  useEffect(() => {
    // Access lives only in memory, so on every page load we restore the
    // session from the httpOnly refresh cookie before anything else runs.
    (async () => {
      try {
        await refreshAccessToken();
        const me = await authApi.me();
        setUser(me.data);
        scheduleSilentRefresh();
      } catch {
        clearAccess();
      } finally {
        setLoading(false);
      }
    })();

    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [scheduleSilentRefresh]);

  const login = async (email, password) => {
    const { data } = await authApi.login({ email, password });
    setAccess(data.access, decodeJwtExp(data.access));
    const me = await authApi.me();
    setUser(me.data);
    scheduleSilentRefresh();
  };

  const logout = async () => {
    if (timerRef.current) clearTimeout(timerRef.current);
    try {
      await authApi.logout();
    } catch {
      // best-effort: clear local state regardless of network failure
    }
    clearAccess();
    setUser(null);
    window.location.href = "/login";
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
