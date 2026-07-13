import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ADMIN_STATUS_OPTIONS, formatWaitTime } from "@/entities/application/lib/constants";

describe("ADMIN_STATUS_OPTIONS", () => {
  it("includes MANUAL_REVIEW, since the underwriter queue filters on it", () => {
    expect(ADMIN_STATUS_OPTIONS.map((o) => o.value)).toContain("MANUAL_REVIEW");
  });
});

describe("formatWaitTime", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-07-13T12:00:00Z"));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns an em dash for a missing date", () => {
    expect(formatWaitTime(null)).toBe("—");
    expect(formatWaitTime(undefined)).toBe("—");
  });

  it("formats sub-hour waits in minutes", () => {
    expect(formatWaitTime("2026-07-13T11:30:00Z")).toBe("30 мин");
  });

  it("formats sub-day waits in hours", () => {
    expect(formatWaitTime("2026-07-13T02:00:00Z")).toBe("10 ч");
  });

  it("formats multi-day waits in days", () => {
    expect(formatWaitTime("2026-07-10T12:00:00Z")).toBe("3 дн");
  });
});
