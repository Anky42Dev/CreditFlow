import { test, expect } from "@playwright/test";
import { login } from "./utils/login";

// Ports DOC 6 §9.1 item 3: "Silent refresh: истечение access не разлогинивает
// пользователя". Rather than waiting out a real token lifetime, this
// simulates expiry by making the *next* API call return 401 once — the
// same trigger shared/api/client.js's response interceptor reacts to in
// production when the access token has actually expired.

test("a single 401 triggers a transparent refresh, not a logout", async ({ page }) => {
  await login(page, "client@test.com");
  await page.goto("/notifications");

  let refreshCalls = 0;
  let forcedOnce = false;
  await page.route("**/api/v1/notifications*", async (route) => {
    if (!forcedOnce) {
      forcedOnce = true;
      await route.fulfill({ status: 401, json: { detail: "expired" } });
      return;
    }
    await route.continue();
  });
  await page.route("**/api/v1/auth/refresh", async (route) => {
    refreshCalls++;
    await route.continue();
  });

  await page.goto("/notifications");

  // Should stay on the page (no forced redirect to /login) and issue a
  // refresh call to recover the session.
  await expect(page).not.toHaveURL(/\/login/, { timeout: 10000 });
  await expect.poll(() => refreshCalls, { timeout: 10000 }).toBeGreaterThanOrEqual(1);
});
