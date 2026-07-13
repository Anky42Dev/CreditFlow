const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const wsUrl = process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000";
const isDev = process.env.NODE_ENV === "development";

// DOC 6 §3.4: CSP + baseline security headers. Nonce-based script-src would
// force every page into dynamic rendering app-wide (see Next.js CSP guide),
// which conflicts with the static/ISR optimization this same roadmap plans
// for later — so this follows Next's documented no-nonce fallback instead.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob: " + apiUrl,
  "font-src 'self'",
  `connect-src 'self' ${apiUrl} ${wsUrl}`,
  "frame-src 'none'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
].join("; ");

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    root: import.meta.dirname,
  },
  // DOC 6 §7.2: readable stack traces for the monitoring integration.
  productionBrowserSourceMaps: true,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
