import { test, expect } from "@playwright/test";
import { login } from "./utils/login";

// Ports verify_stage6.mjs's AC-7 (infinite scroll triggers paginated fetches)
// and AC-8 (code splitting: /admin/* pulls its own JS chunk) manual checks.

test("AC-7: scrolling the admin applications list fetches further pages", async ({ page }) => {
  await login(page, "admin@test.com");

  const pageRequests = [];
  page.on("request", (req) => {
    const url = req.url();
    if (url.includes("/admin/applications") && url.includes("page=")) pageRequests.push(url);
  });

  await page.goto("/admin/applications");
  await expect(page.locator('a[href^="/admin/applications/"]').first()).toBeVisible({ timeout: 10000 });

  // Scroll the virtualized viewport repeatedly to trigger fetchNextPage.
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 2000);
    await page.evaluate(() => {
      const el =
        document.querySelector("div[style*='overflow: auto']") ||
        document.querySelector("div[style*='overflow']");
      if (el) el.scrollTop = el.scrollHeight;
    });
    await page.waitForTimeout(400);
  }

  await expect.poll(() => pageRequests.length, { timeout: 5000 }).toBeGreaterThanOrEqual(2);
});

test("AC-8: entering /admin/* loads a separate JS chunk not fetched on the client pages", async ({ page }) => {
  await login(page, "admin@test.com");

  await page.goto("/applications");
  const chunksBeforeAdmin = new Set();
  page.on("response", (res) => {
    if (res.url().endsWith(".js")) chunksBeforeAdmin.add(res.url());
  });
  await page.waitForTimeout(800);
  const knownBefore = new Set(chunksBeforeAdmin);

  const newChunks = [];
  page.on("response", (res) => {
    const url = res.url();
    if (url.endsWith(".js") && !knownBefore.has(url)) newChunks.push(url);
  });

  await page.goto("/admin/applications");
  await expect.poll(() => newChunks.length, { timeout: 5000 }).toBeGreaterThan(0);
});
