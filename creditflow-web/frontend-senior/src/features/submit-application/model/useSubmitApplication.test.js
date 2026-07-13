import { describe, expect, it } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { createQueryWrapper } from "@/test/utils/createQueryWrapper";
import { useSubmitApplication } from "@/features/submit-application/model/useSubmitApplication";
import { applicationKeys } from "@/entities/application/model/keys";

describe("useSubmitApplication", () => {
  it("submits the application and invalidates its list + detail caches", async () => {
    const { queryClient, wrapper } = createQueryWrapper();

    // Pre-seed the caches this hook is expected to invalidate on success,
    // so we can assert they actually go stale.
    queryClient.setQueryData(applicationKeys.list({}), { results: [] });
    queryClient.setQueryData(applicationKeys.detail(1), { id: 1, status: "DRAFT" });

    const { result } = renderHook(() => useSubmitApplication(1), { wrapper });

    await act(async () => {
      await result.current.mutateAsync();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data.status).toBe("SUBMITTED");

    expect(queryClient.getQueryState(applicationKeys.list({}))?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(applicationKeys.detail(1))?.isInvalidated).toBe(true);
  });

  it("surfaces the error and does not touch the cache when the API call fails", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/credit-applications/:id/submit", () => {
        return HttpResponse.json({ error: { code: "VALIDATION" } }, { status: 400 });
      })
    );

    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(applicationKeys.detail(1), { id: 1, status: "DRAFT" });

    const { result } = renderHook(() => useSubmitApplication(1), { wrapper });

    await act(async () => {
      await result.current.mutateAsync().catch(() => {});
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(queryClient.getQueryState(applicationKeys.detail(1))?.isInvalidated).toBe(false);
  });
});
