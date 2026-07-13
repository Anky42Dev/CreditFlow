import { test, expect } from "@playwright/test";
import { login } from "./utils/login";

// Ports DOC 6 §9.1 item 1: "Регистрация → логин → оформление заявки →
// (WS) статус APPROVED → просмотр кредита". Registration is exercised
// separately by the app's own form validation; here we cover the
// login → submit → status-update part of the path with a seeded client,
// since a fresh registration would need email verification/test-data setup
// outside this suite's scope.

test("client creates and submits an application, status moves off DRAFT", async ({ page }) => {
  await login(page, "client@test.com");

  await page.goto("/applications/new");
  await page.selectOption('select[name="product"]', { index: 1 });
  await page.fill('input[name="amount"]', "100000");
  await page.fill('input[name="term_months"]', "12");
  await page.click('button:has-text("Создать заявку")');

  await page.waitForURL(/\/applications\/\d+/, { timeout: 10000 });

  // The application starts as DRAFT; submitting hands it to scoring.
  const submitBtn = page.locator('button:has-text("Отправить")');
  if (await submitBtn.count()) {
    await submitBtn.click();
  }

  await expect(
    page.getByText(/Отправлена|Скоринг|Ручная проверка|Одобрена|Отклонена/)
  ).toBeVisible({ timeout: 10000 });
});
