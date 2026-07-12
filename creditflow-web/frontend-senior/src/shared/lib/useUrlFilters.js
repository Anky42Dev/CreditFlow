"use client";

import { useCallback, useMemo } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";

/**
 * Syncs a flat filters object with the URL query string so filter state is
 * shareable and survives reload (DOC 4 §8). `arrayKeys` lists which filter
 * keys are read/written as repeated params (?status=A&status=B) instead of
 * a single value — must be called with a stable array (define outside the
 * component or wrap in useMemo) since it's a hook dependency.
 */
export function useUrlFilters(arrayKeys = []) {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const searchParamsString = searchParams.toString();

  const filters = useMemo(() => {
    const params = new URLSearchParams(searchParamsString);
    const result = {};
    for (const key of params.keys()) {
      if (key === "page") continue;
      result[key] = arrayKeys.includes(key) ? params.getAll(key) : params.get(key);
    }
    for (const key of arrayKeys) {
      if (!(key in result)) result[key] = [];
    }
    return result;
  }, [searchParamsString, arrayKeys]);

  const page = Number(searchParams.get("page")) || 1;

  const push = useCallback(
    (next) => router.push(`${pathname}?${next.toString()}`, { scroll: false }),
    [router, pathname]
  );

  const setField = useCallback(
    (key, value) => {
      const next = new URLSearchParams(searchParamsString);
      next.delete(key);
      const isEmpty =
        value === undefined ||
        value === null ||
        value === "" ||
        (Array.isArray(value) && value.length === 0);
      if (!isEmpty) {
        if (Array.isArray(value)) value.forEach((v) => next.append(key, v));
        else next.set(key, value);
      }
      next.set("page", "1");
      push(next);
    },
    [searchParamsString, push]
  );

  const setPage = useCallback(
    (nextPage) => {
      const next = new URLSearchParams(searchParamsString);
      next.set("page", String(nextPage));
      push(next);
    },
    [searchParamsString, push]
  );

  return { filters, page, setField, setPage };
}
