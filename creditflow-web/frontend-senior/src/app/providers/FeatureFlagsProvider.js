"use client";

import { createContext, useContext, useEffect, useState } from "react";
import api from "@/shared/api/client";
import { useAuth } from "@/entities/user/model/useAuth";

// DOC 6 §6 + §11: feature flags are a single source of truth with the
// backend — GET /feature-flags returns a flat `{ [flagName]: boolean }`
// map for the current user (global + percentage rollout resolved
// server-side, see DOC 5 §11). The frontend only reads.
const FeatureFlagsContext = createContext({});

export function useFlag(name) {
  return useContext(FeatureFlagsContext)[name] ?? false;
}

export function FeatureFlagsProvider({ children }) {
  // Placed below AuthProvider in app/layout.js on purpose: GET
  // /feature-flags is personalized per user, so it must be requested
  // only once an access token exists in memory (shared/api/authStore)
  // and re-requested whenever the logged-in user changes.
  const { user } = useAuth();
  const [flags, setFlags] = useState({});

  useEffect(() => {
    // Same convention as WebSocketProvider: we don't defensively reset
    // state to {} when `user` clears, because AuthProvider.logout()
    // always does a hard `window.location.href` redirect, which remounts
    // the whole provider tree anyway — an explicit reset here would only
    // add a synchronous setState-in-effect for no observable benefit.
    if (!user) return;
    (async () => {
      try {
        const { data } = await api.get("/feature-flags");
        setFlags(data ?? {});
      } catch {
        // Fail closed: if the flags request errors out, useFlag() falls
        // back to `false` for everything (see default above), which is
        // the safe state for a gradual/kill-switch rollout mechanism.
        setFlags({});
      }
    })();
  }, [user]);

  return (
    <FeatureFlagsContext.Provider value={flags}>
      {children}
    </FeatureFlagsContext.Provider>
  );
}
