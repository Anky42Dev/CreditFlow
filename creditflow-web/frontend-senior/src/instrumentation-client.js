// Next.js client instrumentation: runs after the HTML loads, before
// hydration. This is where DOC 6 §7.2's global error listeners and §8's
// Web Vitals reporting get wired up.
import { reportError, pushBreadcrumb } from "@/shared/lib/monitoring";
import { initWebVitals } from "@/app/reportWebVitals";

window.addEventListener("error", (event) => {
  reportError(event.error || event.message, { source: "window.error" });
});

window.addEventListener("unhandledrejection", (event) => {
  reportError(event.reason, { source: "unhandledrejection" });
});

initWebVitals();

export function onRouterTransitionStart(url, navigationType) {
  pushBreadcrumb({ category: "navigation", message: `${navigationType} → ${url}` });
}
