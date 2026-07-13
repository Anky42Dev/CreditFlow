"use client";

import { useContext, useEffect } from "react";
import { WSContext } from "@/app/providers/WebSocketProvider";
import { useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import {
  applicationKeys,
  adminApplicationKeys,
} from "@/entities/application/model/keys";
import { notificationKeys } from "@/entities/notification/model/keys";

// Patches the matching row's `status` inside a paginated
// { count, next, previous, results } page, leaving everything else
// (including rows that don't match) untouched. No-op if the page isn't
// cached yet or doesn't contain this id.
function patchApplicationInPage(page, applicationId, status) {
  if (!page?.results) return page;
  const idx = page.results.findIndex((a) => a.id === applicationId);
  if (idx === -1) return page;
  const results = [...page.results];
  results[idx] = { ...results[idx], status };
  return { ...page, results };
}

export function useWSEvents() {
  const { lastEvent } = useContext(WSContext);
  const qc = useQueryClient();

  useEffect(() => {
    if (!lastEvent) return;
    switch (lastEvent.event) {
      case "application_status": {
        const { application_id: applicationId, status } = lastEvent;

        // Detail caches: patch in place, but only if already cached —
        // the socket payload only carries {application_id, status}, not
        // a full application object, so we must not fabricate one.
        qc.setQueryData(applicationKeys.detail(applicationId), (old) =>
          old ? { ...old, status } : old
        );
        qc.setQueryData(adminApplicationKeys.detail(applicationId), (old) =>
          old ? { ...old, status } : old
        );

        // List caches (client + admin, including admin's infinite-scroll
        // variant): patch the row's status in every currently cached
        // page/filter across applicationKeys.lists() /
        // adminApplicationKeys.lists(). setQueriesData matches by key
        // prefix, same as the invalidateQueries calls this replaces.
        //
        // Known trade-off: this fixes the row's *fields* but not its
        // *membership* — e.g. an admin list filtered by status=PENDING
        // should technically drop a row that just became APPROVED. We
        // accept that here instead of a full invalidateQueries per
        // event; the short staleTime (15s admin / 30s client, see
        // useApplications/useAdminApplications) reconciles membership
        // on the next background refetch.
        qc.setQueriesData({ queryKey: applicationKeys.lists() }, (page) =>
          patchApplicationInPage(page, applicationId, status)
        );
        qc.setQueriesData({ queryKey: adminApplicationKeys.lists() }, (page) =>
          patchApplicationInPage(page, applicationId, status)
        );
        qc.setQueriesData(
          { queryKey: adminApplicationKeys.infiniteLists() },
          (data) =>
            data?.pages
              ? {
                  ...data,
                  pages: data.pages.map((page) =>
                    patchApplicationInPage(page, applicationId, status)
                  ),
                }
              : data
        );

        toast(`Заявка #${applicationId}: ${status}`);
        break;
      }
      case "notification":
        // The unread counter is a single well-known key holding a plain
        // number — safe to bump immediately without a round-trip.
        qc.setQueryData(notificationKeys.unreadCount, (n) =>
          typeof n === "number" ? n + 1 : n
        );
        // The notification *list*, unlike the counter, can't be
        // point-patched here: it's paginated and filtered by `is_read`
        // (see useNotifications), and the socket payload doesn't tell us
        // which page a brand-new notification would land on or whether
        // it matches the currently active filter. Falling back to
        // invalidation for the list only.
        qc.invalidateQueries({ queryKey: notificationKeys.lists() });
        toast(lastEvent.title);
        break;
      case "payment_due":
        // Informational only — no cached entity changes as a result of
        // this event, so there's nothing to patch or invalidate.
        toast(`Приближается платёж по кредиту #${lastEvent.loan_id}`);
        break;
    }
  }, [lastEvent, qc]);
}
