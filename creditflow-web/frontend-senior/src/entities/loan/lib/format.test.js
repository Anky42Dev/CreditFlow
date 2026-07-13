import { describe, expect, it } from "vitest";
import { getNextPayment } from "@/entities/loan/lib/format";

describe("getNextPayment", () => {
  it("returns null when the loan has no schedule", () => {
    expect(getNextPayment(null)).toBeNull();
    expect(getNextPayment({})).toBeNull();
  });

  it("prioritizes an OVERDUE item over a PENDING one", () => {
    const loan = {
      schedule_items: [
        { id: 1, status: "PAID" },
        { id: 2, status: "PENDING" },
        { id: 3, status: "OVERDUE" },
      ],
    };
    expect(getNextPayment(loan).id).toBe(3);
  });

  it("falls back to the first PENDING item when nothing is overdue", () => {
    const loan = {
      schedule_items: [
        { id: 1, status: "PAID" },
        { id: 2, status: "PENDING" },
        { id: 3, status: "PENDING" },
      ],
    };
    expect(getNextPayment(loan).id).toBe(2);
  });

  it("returns null when every item is already PAID", () => {
    const loan = {
      schedule_items: [
        { id: 1, status: "PAID" },
        { id: 2, status: "PAID" },
      ],
    };
    expect(getNextPayment(loan)).toBeNull();
  });
});
