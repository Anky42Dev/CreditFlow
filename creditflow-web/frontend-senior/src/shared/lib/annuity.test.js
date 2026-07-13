import { describe, expect, it } from "vitest";
import { calcAnnuity } from "@/shared/lib/annuity";

describe("calcAnnuity", () => {
  it("returns null for missing/zero/negative inputs", () => {
    expect(calcAnnuity(0, 12, 12)).toBeNull();
    expect(calcAnnuity(100000, 12, 0)).toBeNull();
    expect(calcAnnuity(-1, 12, 12)).toBeNull();
    expect(calcAnnuity(undefined, 12, 12)).toBeNull();
  });

  it("splits the amount evenly across months when the rate is 0", () => {
    expect(calcAnnuity(120000, 0, 12)).toBe(10000);
  });

  it("computes the standard annuity payment formula for a nonzero rate", () => {
    const amount = 100000;
    const rate = 12; // annual %, matches product.interest_rate shape from the API
    const months = 12;
    const r = rate / 100 / 12;
    const factor = Math.pow(1 + r, months);
    const expected = (amount * r * factor) / (factor - 1);
    expect(calcAnnuity(amount, rate, months)).toBeCloseTo(expected, 6);
  });

  it("accepts string inputs, since form fields deliver strings", () => {
    expect(calcAnnuity("120000", "0", "12")).toBe(10000);
  });
});
