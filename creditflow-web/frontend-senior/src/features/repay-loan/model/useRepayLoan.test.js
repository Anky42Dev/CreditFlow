import { describe, expect, it } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "@/test/mocks/server";
import { createQueryWrapper } from "@/test/utils/createQueryWrapper";
import { useRepayLoan } from "@/features/repay-loan/model/useRepayLoan";
import { loanKeys } from "@/entities/loan/model/keys";

describe("useRepayLoan", () => {
  it("sends the idempotency key through and invalidates the loan caches on success", async () => {
    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(loanKeys.list({}), { results: [] });
    queryClient.setQueryData(loanKeys.detail(7), { id: 7, status: "ACTIVE" });

    const { result } = renderHook(() => useRepayLoan(7), { wrapper });

    await act(async () => {
      await result.current.mutateAsync({ amount: "9000.00", idempotency_key: "key-123" });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data.idempotency_key).toBe("key-123");
    expect(result.current.data.amount).toBe("9000.00");

    expect(queryClient.getQueryState(loanKeys.list({}))?.isInvalidated).toBe(true);
    expect(queryClient.getQueryState(loanKeys.detail(7))?.isInvalidated).toBe(true);
  });

  it("surfaces a 409 DUPLICATE error from a repeated repay without invalidating the cache", async () => {
    server.use(
      http.post("http://localhost:8000/api/v1/loans/:id/repay", () => {
        return HttpResponse.json({ error: { code: "DUPLICATE" } }, { status: 409 });
      })
    );

    const { queryClient, wrapper } = createQueryWrapper();
    queryClient.setQueryData(loanKeys.detail(7), { id: 7, status: "ACTIVE" });

    const { result } = renderHook(() => useRepayLoan(7), { wrapper });

    await act(async () => {
      await result.current
        .mutateAsync({ amount: "9000.00", idempotency_key: "key-123" })
        .catch(() => {});
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error.response.data.error.code).toBe("DUPLICATE");
    expect(queryClient.getQueryState(loanKeys.detail(7))?.isInvalidated).toBe(false);
  });
});
