import { describe, expect, it } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { createQueryWrapper } from "@/test/utils/createQueryWrapper";
import { useReadNotification, useReadAllNotifications } from "@/features/mark-read/model/useMarkRead";
import { notificationKeys } from "@/entities/notification/model/keys";

describe("useReadNotification", () => {
  it("optimistically decrements the unread count before the request resolves", async () => {
    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(notificationKeys.unreadCount, 3);

    const { result } = renderHook(() => useReadNotification(), { wrapper });

    act(() => {
      result.current.mutate(42);
    });

    // The optimistic onMutate patch happens synchronously, ahead of the
    // (mocked) network round-trip resolving.
    await waitFor(() => expect(queryClient.getQueryData(notificationKeys.unreadCount)).toBe(2));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("rolls back the optimistic decrement when the request fails", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/notifications/:id/read", () => {
        return HttpResponse.json({ error: { code: "SERVER_ERROR" } }, { status: 500 });
      })
    );

    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(notificationKeys.unreadCount, 3);

    const { result } = renderHook(() => useReadNotification(), { wrapper });

    await act(async () => {
      await result.current.mutateAsync(42).catch(() => {});
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryData(notificationKeys.unreadCount)).toBe(3);
  });
});

describe("useReadAllNotifications", () => {
  it("optimistically zeroes the unread count", async () => {
    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(notificationKeys.unreadCount, 5);

    const { result } = renderHook(() => useReadAllNotifications(), { wrapper });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(queryClient.getQueryData(notificationKeys.unreadCount)).toBe(0));
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
