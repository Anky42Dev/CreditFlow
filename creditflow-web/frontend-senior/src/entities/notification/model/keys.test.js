import { describe, expect, it } from "vitest";
import { notificationKeys } from "@/entities/notification/model/keys";

describe("notificationKeys", () => {
  it("builds the base list key and scopes by filters", () => {
    expect(notificationKeys.all).toEqual(["notifications"]);
    expect(notificationKeys.list({ is_read: false })).toEqual([
      "notifications",
      "list",
      { is_read: false },
    ]);
  });

  it("exposes a dedicated unread-count key, separate from the lists", () => {
    expect(notificationKeys.unreadCount).toEqual(["unread-count"]);
  });
});
