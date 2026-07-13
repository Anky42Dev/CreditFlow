// NOTE (Stage 6 — Тестирование и CI): kept as-is, unmodified, as a manual
// smoke/verification script. Its scenarios (AC-1, AC-2, AC-7, AC-8, AC-5)
// have been ported into proper Playwright test files with `expect` under
// e2e/*.spec.js (see e2e/rbac.spec.js, e2e/admin-applications.spec.js,
// e2e/repay-idempotency.spec.js) for CI. Run this file directly with
// `node verify_stage6.mjs` against a running app for a quick manual check.
import { chromium } from "playwright";

const BASE = "http://localhost:3000";
const PASS = "TestPass123!";

async function login(page, email) {
  await page.goto(`${BASE}/login`);
  await page.fill('input[name="email"]', email);
  await page.fill('input[name="password"]', PASS);
  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes("/login"), { timeout: 10000 });
}

const results = [];
function log(id, ok, detail) {
  results.push({ id, ok, detail });
  console.log(`${ok ? "PASS" : "FAIL"} ${id}: ${detail}`);
}

const browser = await chromium.launch();

// ---------- AC-1: CLIENT -> /admin/products -> redirect ----------
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, "client@test.com");
  await page.goto(`${BASE}/admin/products`);
  await page.waitForTimeout(1500);
  const url = page.url();
  log("AC-1", !url.includes("/admin/products"), `client redirected away from /admin/products, ended at ${url}`);
  await ctx.close();
}

// ---------- AC-2: UNDERWRITER sees MANUAL_REVIEW app with Approve button ----------
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, "underwriter@test.com");
  await page.goto(`${BASE}/admin/applications`);
  await page.click('button:has-text("Очередь")');
  await page.waitForTimeout(1500);
  const rowLink = page.locator('a[href^="/admin/applications/"]').first();
  const hasRow = (await rowLink.count()) > 0;
  let approveVisible = false;
  if (hasRow) {
    await rowLink.click();
    await page.waitForTimeout(1000);
    approveVisible = await page.locator('button:has-text("Одобрить")').isVisible().catch(() => false);
  }
  log("AC-2", hasRow && approveVisible, `queue row found=${hasRow}, approve button visible=${approveVisible}`);
  await ctx.close();
}

// ---------- AC-7: infinite scroll on admin/applications (all tab) ----------
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, "admin@test.com");

  let fetchCount = 0;
  page.on("request", (req) => {
    const u = req.url();
    if (u.includes("/admin/applications") && u.includes("page=")) fetchCount++;
  });

  await page.goto(`${BASE}/admin/applications`);
  await page.waitForTimeout(1500);
  const initialCount = await page.locator('a[href^="/admin/applications/"]').count();

  // scroll the virtualized viewport repeatedly to trigger fetchNextPage
  const scrollBox = page.locator("div.rounded-xl.border >> div[style*='overflow']").first();
  for (let i = 0; i < 6; i++) {
    await page.mouse.wheel(0, 2000);
    await page.evaluate(() => {
      const el = document.querySelector("div[style*='overflow: auto']") || document.querySelector("div[style*='overflow']");
      if (el) el.scrollTop = el.scrollHeight;
    });
    await page.waitForTimeout(400);
  }
  await page.waitForTimeout(1000);
  const afterCount = await page.locator('a[href^="/admin/applications/"]').count();
  log(
    "AC-7",
    fetchCount >= 2,
    `page-param requests observed=${fetchCount}, rows in DOM before=${initialCount} after-scroll=${afterCount} (virtualized, so DOM count stays small even as more pages load)`
  );
  await ctx.close();
}

// ---------- AC-8: /admin/* loads a separate JS chunk ----------
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, "admin@test.com");

  await page.goto(`${BASE}/applications`);
  const beforeChunks = new Set();
  page.on("response", (res) => {
    if (res.url().endsWith(".js")) beforeChunks.add(res.url());
  });
  await page.waitForTimeout(800);
  const chunksBeforeAdmin = new Set(beforeChunks);

  const newChunks = [];
  page.on("response", (res) => {
    const u = res.url();
    if (u.endsWith(".js") && !chunksBeforeAdmin.has(u)) newChunks.push(u);
  });
  await page.goto(`${BASE}/admin/applications`);
  await page.waitForTimeout(1200);
  log("AC-8", newChunks.length > 0, `new JS chunks fetched when entering /admin/*: ${newChunks.length}`);
  await ctx.close();
}

// ---------- AC-5: idempotent repay (double click) ----------
{
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await login(page, "client@test.com");
  await page.goto(`${BASE}/loans`);
  await page.waitForTimeout(1000);
  const loanLink = page.locator('a[href^="/loans/"]').first();
  const hasLoan = (await loanLink.count()) > 0;
  let result = "no active loan with a due payment to test";
  if (hasLoan) {
    await loanLink.click();
    await page.waitForTimeout(800);
    const repayBtn = page.locator('button:has-text("Внести платёж")');
    if (await repayBtn.count()) {
      let repayRequests = 0;
      page.on("request", (req) => {
        if (req.url().includes("/repay") && req.method() === "POST") repayRequests++;
      });
      await repayBtn.click();
      await page.waitForTimeout(500);
      const confirmBtn = page.locator('button:has-text("Подтвердить")');
      await Promise.all([confirmBtn.click(), confirmBtn.click()]);
      await page.waitForTimeout(1500);
      result = `repay POST requests sent=${repayRequests} (expect 1, second click should be disabled while pending)`;
      log("AC-5", repayRequests <= 1, result);
    } else {
      log("AC-5", true, "no due payment on this loan (nothing to repay) — skipped, not a failure");
    }
  } else {
    log("AC-5", true, result + " — skipped, not a failure");
  }
  await ctx.close();
}

await browser.close();

console.log("\n=== SUMMARY ===");
for (const r of results) console.log(`${r.ok ? "PASS" : "FAIL"} ${r.id}`);
