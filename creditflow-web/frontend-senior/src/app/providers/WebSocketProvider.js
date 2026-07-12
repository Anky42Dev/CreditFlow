"use client";

import { createContext, useEffect, useRef, useState } from "react";
import { getTokens } from "@/shared/api/tokenStorage";
import { useAuth } from "@/entities/user/model/useAuth";

export const WSContext = createContext(null);

export function WebSocketProvider({ children }) {
  const { user } = useAuth();
  const wsRef = useRef(null);
  const [lastEvent, setLastEvent] = useState(null);
  const reconnectRef = useRef(0);

  useEffect(() => {
    if (!user) return;
    let closed = false;
    let reconnectTimer = null;

    const connect = () => {
      const { access } = getTokens();
      const url = `${process.env.NEXT_PUBLIC_WS_URL}/ws/notifications/?token=${access}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        reconnectRef.current = 0;
      };
      ws.onmessage = (e) => setLastEvent(JSON.parse(e.data));
      ws.onclose = () => {
        if (closed) return;
        const delay = Math.min(1000 * 2 ** reconnectRef.current, 30000);
        reconnectRef.current++;
        reconnectTimer = setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      closed = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, [user]);

  return (
    <WSContext.Provider value={{ lastEvent }}>{children}</WSContext.Provider>
  );
}
