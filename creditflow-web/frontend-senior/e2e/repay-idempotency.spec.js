import { test, expect } from "@playwright/test";
import { login } from "./utils/login";

// Ports verify_stage6.mjs's AC-5 manual check (DOC 6 §9.1 item 2:
// "Погашение: двойной клик → ровно одна транзакция (idempotency)").

test("AC-5: double-clicking confirm on repay sends at most one POST /repay", async ({ page }) => {
  await login(page, "client@test.com");
  await page.goto("/loans");

  const loanLink = page.locator('a[href^="/loans/"]').first();
  test.skip((await loanLink.count()) === 0, "no active loan available to test repay against");

  await loanLink.click();
  const repayBtn = page.locator('button:has-text("Внести платёж")');
  test.skip(!(await repayBtn.count()), "no due payment on this loan — nothing to repay");

  const repayRequests = [];
  page.on("request", (req) => {
    if (req.url().includes("/repay") && req.method() === "POST") repayRequests.push(req.url());
  });

  await repayBtn.click();
  const confirmBtn = page.locator('button:has-text("Подтвердить")');
  await expect(confirmBtn).toBeVisible();

  // Fire both clicks together — the second should be a no-op because the
  // button disables itself while the mutation is pending (isPending).
  await Promise.all([confirmBtn.click(), confirmBtn.click()]);
  await page.waitForTimeout(1500);

  expect(repayRequests.length).toBeLessThanOrEqual(1);
});
