import { describe, expect, it } from "vitest";
import { getNotificationLink } from "@/entities/notification/lib/getNotificationLink";

describe("getNotificationLink", () => {
  it("links application.* notifications to /applications/{id}", () => {
    const notification = { type: "application.status_changed", body: "Статус заявки №15 изменён" };
    expect(getNotificationLink(notification)).toBe("/applications/15");
  });

  it("links loan.* notifications to /loans/{id}", () => {
    const notification = { type: "loan.disbursed", body: "Кредит №3 выдан" };
    expect(getNotificationLink(notification)).toBe("/loans/3");
  });

  it("links payment.* notifications to /loans/{id} as well", () => {
    const notification = { type: "payment.received", body: "Платёж по кредиту №8 получен" };
    expect(getNotificationLink(notification)).toBe("/loans/8");
  });

  it("returns null when the body has no №{id} reference", () => {
    const notification = { type: "application.status_changed", body: "Без ссылки на объект" };
    expect(getNotificationLink(notification)).toBeNull();
  });

  it("returns null for an unrecognized type prefix", () => {
    const notification = { type: "system.announcement", body: "Объект №1" };
    expect(getNotificationLink(notification)).toBeNull();
  });

  it("returns null for a missing/undefined notification", () => {
    expect(getNotificationLink(undefined)).toBeNull();
    expect(getNotificationLink({})).toBeNull();
  });
});
