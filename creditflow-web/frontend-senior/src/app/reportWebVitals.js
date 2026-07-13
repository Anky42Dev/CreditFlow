// DOC 6 §8: Web Vitals reporting via the web-vitals package, sent with
// navigator.sendBeacon so metrics survive page unload.
import { onCLS, onINP, onLCP } from "web-vitals";

const ANALYTICS_ENDPOINT = "/analytics";

function send(metric) {
  const body = JSON.stringify(metric);
  if (typeof navigator !== "undefined" && navigator.sendBeacon) {
    navigator.sendBeacon(ANALYTICS_ENDPOINT, body);
  }
}

export function initWebVitals() {
  onCLS(send);
  onINP(send);
  onLCP(send);
}
