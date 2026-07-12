"use client";

import { useContext, useEffect } from "react";
import { WSContext } from "@/lib/ws/WebSocketProvider";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

export function useWSEvents() {
  const { lastEvent } = useContext(WSContext);
  const qc = useQueryClient();

  useEffect(() => {
    if (!lastEvent) return;
    switch (lastEvent.event) {
      case "application_status":
        qc.invalidateQueries({ queryKey: ["applications"] });
        qc.invalidateQueries({
          queryKey: ["application", lastEvent.application_id],
        });
        qc.invalidateQueries({ queryKey: ["admin-applications"] });
        qc.invalidateQueries({
          queryKey: ["admin-application", String(lastEvent.application_id)],
        });
        toast(`Заявка #${lastEvent.application_id}: ${lastEvent.status}`);
        break;
      case "notification":
        qc.invalidateQueries({ queryKey: ["notifications"] });
        qc.invalidateQueries({ queryKey: ["unread-count"] });
        toast(lastEvent.title);
        break;
      case "payment_due":
        toast(`Приближается платёж по кредиту #${lastEvent.loan_id}`);
        break;
    }
  }, [lastEvent, qc]);
}
