const GA_SCRIPT_ID = "student-weather-ga4";
const GA_MEASUREMENT_ID = (import.meta.env.VITE_GA_MEASUREMENT_ID || "G-B7NFVCFTED")?.trim();

const sensitiveQueryKeys = new Set([
  "access_token",
  "api_key",
  "auth",
  "code",
  "credential",
  "email",
  "id_token",
  "jwt",
  "key",
  "lat",
  "latitude",
  "lng",
  "lon",
  "longitude",
  "password",
  "refresh_token",
  "secret",
  "state",
  "token",
]);

const sensitiveKeyFragments = [
  "email",
  "jwt",
  "lat",
  "lng",
  "lon",
  "password",
  "secret",
  "token",
];

export function initGoogleAnalytics(): void {
  console.log("[GA4] initGoogleAnalytics() called");
  const measurementId = getGoogleAnalyticsMeasurementId();
  console.log("[GA4] Measurement ID:", measurementId);
  if (!measurementId) {
    console.warn("[GA4] Measurement ID is missing or invalid. Aborting GA4 initialization.");
    return;
  }
  if (window.__studentWeatherGaInitialized) {
    console.log("[GA4] Already initialized. Skipping duplicate initialization.");
    return;
  }

  window.dataLayer = window.dataLayer ?? [];
  window.gtag =
    window.gtag ??
    ((...args: unknown[]) => {
      window.dataLayer?.push(args);
    });

  if (!document.getElementById(GA_SCRIPT_ID)) {
    console.log("[GA4] Injecting script tag for measurement ID:", measurementId);
    const script = document.createElement("script");
    script.id = GA_SCRIPT_ID;
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    document.head.appendChild(script);
  } else {
    console.log("[GA4] Script tag already injected.");
  }

  const pagePath = sanitizePagePath(`${window.location.pathname}${window.location.search}`);
  window.gtag("js", new Date());
  window.gtag("config", measurementId, buildPageViewParams(pagePath));
  window.__studentWeatherGaInitialized = true;
  window.__studentWeatherGaLastPath = pagePath;
  console.log("[GA4] Google Analytics initialized successfully with page:", pagePath);
}

export function trackPageView(path: string): void {
  console.log("[GA4] trackPageView() called with path:", path);
  const measurementId = getGoogleAnalyticsMeasurementId();
  if (!measurementId) {
    console.warn("[GA4] trackPageView aborted: Measurement ID is missing.");
    return;
  }
  if (!window.__studentWeatherGaInitialized) {
    console.log("[GA4] trackPageView: GA4 not initialized. Initializing now...");
    initGoogleAnalytics();
    return;
  }

  const pagePath = sanitizePagePath(path);
  if (window.__studentWeatherGaLastPath === pagePath) {
    console.log("[GA4] trackPageView: Path hasn't changed. Skipping page view tracking.");
    return;
  }

  window.gtag?.("config", measurementId, buildPageViewParams(pagePath));
  window.__studentWeatherGaLastPath = pagePath;
  console.log("[GA4] Tracked page view for path:", pagePath);
}

export function trackEvent(eventName: string, params: Record<string, unknown> = {}): void {
  console.log("[GA4] trackEvent() called for event:", eventName, "with params:", params);
  const measurementId = getGoogleAnalyticsMeasurementId();
  if (!measurementId) {
    console.warn("[GA4] trackEvent aborted: Measurement ID is missing.");
    return;
  }
  if (!window.__studentWeatherGaInitialized) {
    console.log("[GA4] trackEvent: GA4 not initialized. Initializing now...");
    initGoogleAnalytics();
  }

  const safeEventName = sanitizeEventName(eventName);
  if (!safeEventName) {
    console.warn("[GA4] trackEvent: Event name is invalid after sanitization. Aborting.");
    return;
  }

  window.gtag?.("event", safeEventName, sanitizeEventParams(params));
  console.log("[GA4] Tracked event:", safeEventName);
}

function getGoogleAnalyticsMeasurementId(): string | null {
  if (typeof window === "undefined" || typeof document === "undefined") return null;
  return GA_MEASUREMENT_ID || null;
}

function buildPageViewParams(pagePath: string): Record<string, string> {
  return {
    page_path: pagePath,
    page_location: `${window.location.origin}${pagePath}`,
    page_title: document.title,
  };
}

function sanitizePagePath(path: string): string {
  try {
    const url = new URL(path, window.location.origin);
    for (const key of Array.from(url.searchParams.keys())) {
      if (isSensitiveKey(key)) {
        url.searchParams.delete(key);
      }
    }

    const query = url.searchParams.toString();
    return `${url.pathname}${query ? `?${query}` : ""}`;
  } catch {
    const [pathname = "/"] = path.split("?");
    return pathname.startsWith("/") ? pathname : `/${pathname}`;
  }
}

function sanitizeEventName(eventName: string): string {
  return eventName
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, "_")
    .replace(/_+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 40);
}

function sanitizeEventParams(params: Record<string, unknown>): Record<string, string | number | boolean> {
  const safeParams: Record<string, string | number | boolean> = {};

  for (const [key, value] of Object.entries(params)) {
    if (isSensitiveKey(key)) continue;
    if (typeof value === "string") {
      if (looksSensitiveValue(value)) continue;
      safeParams[key] = value.slice(0, 100);
    } else if (typeof value === "number" && Number.isFinite(value)) {
      safeParams[key] = value;
    } else if (typeof value === "boolean") {
      safeParams[key] = value;
    }
  }

  return safeParams;
}

function isSensitiveKey(key: string): boolean {
  const normalizedKey = key.trim().toLowerCase();
  return (
    sensitiveQueryKeys.has(normalizedKey) ||
    sensitiveKeyFragments.some((fragment) => normalizedKey.includes(fragment))
  );
}

function looksSensitiveValue(value: string): boolean {
  const trimmed = value.trim();
  return trimmed.includes("@") || /^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$/.test(trimmed);
}
