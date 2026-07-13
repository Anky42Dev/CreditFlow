import { describe, expect, it } from "vitest";
import { formatMoney, formatRate } from "@/shared/lib/format";

describe("formatMoney", () => {
  it("formats a numeric value as RUB currency without decimals", () => {
    // Intl inserts a non-breaking space as the thousands separator in ru-RU.
    expect(formatMoney(100000).replace(/\u00A0/g, " ")).toBe("100 000 ₽");
  });

  it("returns an em dash for a non-numeric value", () => {
    expect(formatMoney("not-a-number")).toBe("—");
    expect(formatMoney(undefined)).toBe("—");
  });

  it("accepts numeric strings, since API amounts arrive as strings", () => {
    expect(formatMoney("100000.00").replace(/\u00A0/g, " ")).toBe("100 000 ₽");
  });
});

describe("formatRate", () => {
  it("formats a rate with 2 decimal places and a % suffix", () => {
    expect(formatRate(12)).toBe("12.00%");
    expect(formatRate("9.5")).toBe("9.50%");
  });

  it("returns an em dash for a non-numeric value", () => {
    expect(formatRate("n/a")).toBe("—");
  });
});
