// Mirrors the login() helper in verify_stage6.mjs (same selectors, same
// test password) so both the manual script and this Playwright suite log in
// identically against the seeded test users.
export const TEST_PASSWORD = "TestPass123!";

export async function login(page, email, password = TEST_PASSWORD) {
  await page.goto("/login");
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 });
}
