import { defineConfig } from "vitest/config";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// DOC 6 §9: Vitest for unit/component tests. Alias mirrors jsconfig.json's
// "@/*" -> "./src/*" so test files can import the same way app code does.
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: false,
    setupFiles: ["./src/test/setup.js"],
    include: ["src/**/*.test.{js,jsx}"],
    // Injected before any app module (e.g. shared/api/client.js) reads
    // process.env at import time, so the axios baseURL is deterministic
    // and matches the MSW handlers' base URL.
    env: {
      NEXT_PUBLIC_API_URL: "http://localhost:8000",
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      // Scoped to the files this stage actually adds tests for (utilities,
      // selectors, query-key factories, and the 3 feature hooks) rather than
      // the whole src tree — see docs/06-FRONTEND-SENIOR.md §9/§10.
      include: [
        "src/entities/application/lib/constants.js",
        "src/entities/application/model/keys.js",
        "src/entities/loan/lib/format.js",
        "src/entities/loan/model/keys.js",
        "src/entities/notification/lib/getNotificationLink.js",
        "src/entities/notification/model/keys.js",
        "src/entities/product/model/keys.js",
        "src/shared/lib/annuity.js",
        "src/shared/lib/format.js",
        "src/features/submit-application/model/useSubmitApplication.js",
        "src/features/repay-loan/model/useRepayLoan.js",
        "src/features/mark-read/model/useMarkRead.js",
      ],
      exclude: ["src/test/**"],
      thresholds: {
        lines: 70,
        statements: 70,
        functions: 70,
        branches: 60,
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
