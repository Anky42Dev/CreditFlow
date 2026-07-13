import { defineConfig, devices } from "@playwright/test";

// DOC 6 §9/§9.1: E2E on critical paths, run against a real backend (compose
// stand), not MSW. BASE_URL matches verify_stage6.mjs's default so the two
// can be pointed at the same running app.
const BASE_URL = process.env.E2E_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
