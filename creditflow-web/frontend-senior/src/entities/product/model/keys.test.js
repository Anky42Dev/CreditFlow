import { describe, expect, it } from "vitest";
import { productKeys, adminProductKeys } from "@/entities/product/model/keys";

describe("productKeys", () => {
  it("builds the base list/detail keys", () => {
    expect(productKeys.all).toEqual(["products"]);
    expect(productKeys.detail(3)).toEqual(["products", "detail", 3]);
  });

  it("scopes list keys by filters", () => {
    expect(productKeys.list({ page_size: 100 })).toEqual(["products", "list", { page_size: 100 }]);
  });
});

describe("adminProductKeys", () => {
  it("is a separate cache namespace from the client-facing product keys", () => {
    expect(adminProductKeys.all).toEqual(["admin-products"]);
    expect(adminProductKeys.all).not.toEqual(productKeys.all);
  });
});
