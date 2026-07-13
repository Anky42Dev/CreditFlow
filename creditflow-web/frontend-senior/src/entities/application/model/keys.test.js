import { describe, expect, it } from "vitest";
import { applicationKeys, adminApplicationKeys } from "@/entities/application/model/keys";

describe("applicationKeys", () => {
  it("builds the base list/detail keys", () => {
    expect(applicationKeys.all).toEqual(["applications"]);
    expect(applicationKeys.lists()).toEqual(["applications", "list"]);
    expect(applicationKeys.details()).toEqual(["applications", "detail"]);
  });

  it("includes filters in list keys so different filters get separate cache entries", () => {
    const filters = { status: "SUBMITTED" };
    expect(applicationKeys.list(filters)).toEqual(["applications", "list", filters]);
    expect(applicationKeys.list({})).not.toEqual(applicationKeys.list(filters));
  });

  it("builds a stable detail key per id", () => {
    expect(applicationKeys.detail(5)).toEqual(["applications", "detail", 5]);
    expect(applicationKeys.detail(5)).toEqual(applicationKeys.detail(5));
    expect(applicationKeys.detail(5)).not.toEqual(applicationKeys.detail(6));
  });
});

describe("adminApplicationKeys", () => {
  it("keeps infinite-list keys under the same 'all' prefix as the paginated list", () => {
    // So a single invalidateQueries({queryKey: adminApplicationKeys.all}) after a
    // mutation (approve/reject) also invalidates the infinite-scroll queries.
    expect(adminApplicationKeys.infiniteLists()[0]).toBe(adminApplicationKeys.all[0]);
    expect(adminApplicationKeys.lists()[0]).toBe(adminApplicationKeys.all[0]);
  });

  it("builds distinct keys for the queue filters vs the infinite list", () => {
    const filters = { status: "MANUAL_REVIEW" };
    expect(adminApplicationKeys.list(filters)).toEqual(["admin-applications", "list", filters]);
    expect(adminApplicationKeys.infiniteList(filters)).toEqual([
      "admin-applications",
      "infinite",
      filters,
    ]);
  });

  it("builds a stable detail key per id", () => {
    expect(adminApplicationKeys.detail(9)).toEqual(["admin-applications", "detail", 9]);
  });
});
