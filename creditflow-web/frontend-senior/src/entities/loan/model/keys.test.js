import { describe, expect, it } from "vitest";
import { loanKeys } from "@/entities/loan/model/keys";

describe("loanKeys", () => {
  it("builds the base list/detail keys", () => {
    expect(loanKeys.all).toEqual(["loans"]);
    expect(loanKeys.lists()).toEqual(["loans", "list"]);
    expect(loanKeys.details()).toEqual(["loans", "detail"]);
  });

  it("scopes list keys by filters", () => {
    expect(loanKeys.list({ status: "ACTIVE" })).toEqual(["loans", "list", { status: "ACTIVE" }]);
  });

  it("builds a stable per-id detail key", () => {
    expect(loanKeys.detail(7)).toEqual(["loans", "detail", 7]);
    expect(loanKeys.detail(7)).not.toEqual(loanKeys.detail(8));
  });
});
