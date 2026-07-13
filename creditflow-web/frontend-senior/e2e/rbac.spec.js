import { test, expect } from "@playwright/test";
import { login } from "./utils/login";

// Ports verify_stage6.mjs's AC-1 and AC-2 manual checks into Playwright
// assertions (DOC 6 §9.1 item 4: "RBAC: CLIENT не видит /admin, UNDERWRITER
// одобряет заявку").

test.describe("RBAC", () => {
  test("AC-1: CLIENT navigating to /admin/products is redirected away", async ({ page }) => {
    await login(page, "client@test.com");
    await page.goto("/admin/products");
    await expect(page).not.toHaveURL(/\/admin\/products/, { timeout: 10000 });
  });

  test("AC-2: UNDERWRITER sees a MANUAL_REVIEW application with an Approve action", async ({ page }) => {
    await login(page, "underwriter@test.com");
    await page.goto("/admin/applications");
    await page.click('button:has-text("Очередь")');

    const rowLink = page.locator('a[href^="/admin/applications/"]').first();
    await expect(rowLink).toBeVisible({ timeout: 10000 });

    await rowLink.click();
    await expect(page.locator('button:has-text("Одобрить")')).toBeVisible({ timeout: 10000 });
  });
});
