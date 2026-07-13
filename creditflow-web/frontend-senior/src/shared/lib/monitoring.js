// DOC 6 §7.2: error monitoring. No APM SDK is installed yet, so this module
// logs locally and exposes a single extension point (setErrorTransport) where
// a real service (Sentry, etc.) can be wired in later without touching call
// sites — reportError(error, context) stays the same either way.

const MAX_BREADCRUMBS = 20;
const breadcrumbs = [];

const PII_KEY_PATTERN = /password|token|secret|authorization|access|refresh|csrf|card|passport|ssn|iin/i;
const EMAIL_PATTERN = /[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}/gi;
const JWT_PATTERN = /\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b/g;
const CARD_PATTERN = /\b(?:\d[ -]?){13,19}\b/g;

function scrubString(value) {
  return value
    .replace(JWT_PATTERN, "[REDACTED_JWT]")
    .replace(EMAIL_PATTERN, "[REDACTED_EMAIL]")
    .replace(CARD_PATTERN, "[REDACTED_NUMBER]");
}

function scrubValue(value, depth = 0) {
  if (depth > 5 || value == null) return value;
  if (typeof value === "string") return scrubString(value);
  if (Array.isArray(value)) return value.map((v) => scrubValue(v, depth + 1));
  if (typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, val]) => [
        key,
        PII_KEY_PATTERN.test(key) ? "[REDACTED]" : scrubValue(val, depth + 1),
      ])
    );
  }
  return value;
}

let transport = (payload) => {
  // Extension point: replace with a real APM SDK call, e.g.
  // Sentry.captureException(payload.error, { extra: payload.context, breadcrumbs: payload.breadcrumbs })
  console.error("[monitoring]", payload);
};

export function setErrorTransport(fn) {
  transport = fn;
}

export function pushBreadcrumb(breadcrumb) {
  breadcrumbs.push({ timestamp: new Date().toISOString(), ...scrubValue(breadcrumb) });
  if (breadcrumbs.length > MAX_BREADCRUMBS) breadcrumbs.shift();
}

export function reportError(error, context = {}) {
  const normalized = error instanceof Error ? error : new Error(String(error));

  const payload = {
    message: scrubString(normalized.message || "Unknown error"),
    stack: normalized.stack ? scrubString(normalized.stack) : undefined,
    context: scrubValue(context),
    breadcrumbs: [...breadcrumbs],
    url: typeof window !== "undefined" ? window.location.href : undefined,
    timestamp: new Date().toISOString(),
  };

  transport({ error: normalized, ...payload });
}
