/**
 * ForgeBase Analytics SDK — 1b.1.1, 1b.5.1
 *
 * Client-side event tracking library.
 * - Manages first-party visitor_id cookie (1-year TTL)
 * - Manages session_id via sessionStorage (expires with tab close)
 * - Sends events to /api/v1/tracking/events (or batches via sendBeacon)
 * - Fires parallel GA4 events if gtag() is present on the page
 * - Includes offline queue (localStorage) with auto-flush on reconnect
 *
 * Usage in Client Components:
 *   import { track } from "@/lib/analytics";
 *   track("product_view", { page_type: "product", page_id: product.id });
 *
 * Usage in Server-rendered pages:
 *   import { PageViewTracker } from "@/components/tracking/PageViewTracker";
 *   <PageViewTracker pageType="product" pageId={product.id} />
 *
 * IMPORTANT: This module is client-only. Never import in Server Components.
 */

export type EventName =
  | "page_view"
  | "category_view"
  | "product_view"
  | "application_view"
  | "faq_expand"
  | "comparison_view"
  | "spec_download"
  | "certification_view"
  | "cta_click"
  | "cta_impression"
  | "form_start"
  | "form_submit"
  | "rfq_start"
  | "rfq_submit"
  | "return_visit"
  | "session_depth_reached"
  | "chat_start"
  | "chat_rfq_handoff";

export interface TrackPayload {
  event_name: EventName;
  session_id?: string;
  visitor_id?: string;
  page_url?: string;
  page_type?: string;
  page_id?: string;
  locale?: string;
  referrer?: string;
  campaign_id?: string;
  properties?: Record<string, unknown>;
  analytics_consent: true;
}

// ── Config ────────────────────────────────────────────────────────────────────

// Public browser traffic must remain same-origin so the API receives the
// exact tenant/custom Host selected by the visitor.
const API_ENDPOINT = "";
const TRACKING_DISABLED =
  typeof process !== "undefined" &&
  process.env?.NEXT_PUBLIC_TRACKING_DISABLED === "true";
const EVENTS_URL = `${API_ENDPOINT}/api/v1/tracking/events`;
const VISITOR_COOKIE = "fb_vid";   // first-party cookie name
const SESSION_KEY = "fb_sid";      // sessionStorage key
const SESSION_VISITOR_KEY = "fb_session_vid";
const QUEUE_KEY = "fb_eq";         // localStorage offline queue
const CONSENT_COOKIE = "fb_analytics_consent";
const COOKIE_DAYS = 365;

// ── GA4 Integration (1b.5.1) ─────────────────────────────────────────────────

// Map ForgeBase event names → GA4 standard event names
const GA4_EVENT_MAP: Partial<Record<EventName, string>> = {
  product_view:       "view_item",
  category_view:      "view_item_list",
  rfq_submit:         "generate_lead",
  rfq_start:          "begin_checkout",
  form_submit:        "form_submit",
  spec_download:      "file_download",
  cta_click:          "select_content",
  comparison_view:    "view_item",
};

// Declare gtag on window (loaded externally via <Script> in layout)
declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer?: unknown[];
  }
}

/**
 * Fire a GA4 event in parallel when gtag is available.
 * Silently no-ops if GA4 is not loaded (e.g. adblocker, non-production).
 */
function _fireGA4(
  eventName: EventName,
  properties: Record<string, unknown>
): void {
  if (typeof window === "undefined" || typeof window.gtag !== "function") return;
  const ga4Name = GA4_EVENT_MAP[eventName] ?? `fb_${eventName}`;
  try {
    window.gtag("event", ga4Name, properties);
  } catch {
    // Never let GA4 errors break the first-party tracking
  }
}

// ── Cookie helpers ─────────────────────────────────────────────────────────

function setCookie(name: string, value: string, days: number): void {
  if (typeof document === "undefined") return;
  const expires = new Date(Date.now() + days * 86400_000).toUTCString();
  // SameSite=Lax for first-party use; Secure in production
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax${secure}`;
}

function getCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(?:^|;\\s*)${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

// ── UUID v4 generator (no external dependency) ───────────────────────────────

function uuidv4(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  // Fallback for older environments
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

// ── Visitor & Session identity ────────────────────────────────────────────────

export function getVisitorId(): string {
  if (hasAnalyticsConsent()) {
    let vid = getCookie(VISITOR_COOKIE);
    if (!vid) {
      vid = typeof sessionStorage !== "undefined"
        ? sessionStorage.getItem(SESSION_VISITOR_KEY)
        : null;
      vid ||= uuidv4();
      setCookie(VISITOR_COOKIE, vid, COOKIE_DAYS);
    }
    return vid;
  }
  if (typeof sessionStorage === "undefined") return uuidv4();
  let vid = sessionStorage.getItem(SESSION_VISITOR_KEY);
  if (!vid) {
    vid = uuidv4();
    sessionStorage.setItem(SESSION_VISITOR_KEY, vid);
  }
  return vid;
}

export function hasAnalyticsConsent(): boolean {
  return getCookie(CONSENT_COOKIE) === "granted";
}

export function getAnalyticsVisitorId(): string | null {
  return hasAnalyticsConsent() ? getVisitorId() : null;
}

async function syncAnalyticsConsent(visitorId: string, status: "granted" | "denied" | "revoked"): Promise<void> {
  try {
    await fetch(`${API_ENDPOINT}/api/v1/privacy/analytics-consent`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ visitor_id: visitorId, status, source: "web" }),
      keepalive: true,
    });
  } catch {
    // The local choice still takes effect if the audit endpoint is unavailable.
  }
}

export function setAnalyticsConsent(granted: boolean, revoke = false): void {
  const persistentVisitor = getCookie(VISITOR_COOKIE);
  const sessionVisitor = (
    typeof sessionStorage !== "undefined" ? sessionStorage.getItem(SESSION_VISITOR_KEY) : null
  );
  const visitorId = persistentVisitor || sessionVisitor || uuidv4();
  setCookie(CONSENT_COOKIE, granted ? "granted" : "denied", COOKIE_DAYS);
  if (granted) {
    if (!persistentVisitor) setCookie(VISITOR_COOKIE, visitorId, COOKIE_DAYS);
    void flushQueue();
  } else {
    if (persistentVisitor && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(SESSION_VISITOR_KEY, persistentVisitor);
    }
    setCookie(VISITOR_COOKIE, "", -1);
    if (typeof localStorage !== "undefined") localStorage.removeItem(QUEUE_KEY);
  }
  if (typeof window !== "undefined") {
    window.dispatchEvent(new CustomEvent("forgebase:analytics-consent", { detail: { granted } }));
  }
  void syncAnalyticsConsent(visitorId, granted ? "granted" : (revoke ? "revoked" : "denied"));
}

export function revokeAnalyticsConsent(): void {
  setAnalyticsConsent(false, true);
}

export function getSessionId(): string {
  if (typeof sessionStorage === "undefined") return uuidv4();
  let sid = sessionStorage.getItem(SESSION_KEY);
  if (!sid) {
    sid = uuidv4();
    sessionStorage.setItem(SESSION_KEY, sid);
  }
  return sid;
}

// ── Offline queue ─────────────────────────────────────────────────────────────

function enqueue(payload: TrackPayload): void {
  if (typeof localStorage === "undefined") return;
  try {
    const raw = localStorage.getItem(QUEUE_KEY) || "[]";
    const q: TrackPayload[] = JSON.parse(raw);
    q.push(payload);
    // Cap queue at 50 events to avoid unbounded growth
    if (q.length > 50) q.splice(0, q.length - 50);
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q));
  } catch {
    // localStorage unavailable (private browsing quota) — silently drop
  }
}

async function flushQueue(): Promise<void> {
  if (typeof localStorage === "undefined" || TRACKING_DISABLED || !hasAnalyticsConsent()) return;
  try {
    const raw = localStorage.getItem(QUEUE_KEY) || "[]";
    const q: TrackPayload[] = JSON.parse(raw);
    if (q.length === 0) return;

    // Send in batches of 20 — backend enforces max 20 per batch
    const BATCH_SIZE = 20;
    for (let i = 0; i < q.length; i += BATCH_SIZE) {
      await fetch(`${API_ENDPOINT}/api/v1/tracking/events/batch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(q.slice(i, i + BATCH_SIZE)),
      });
    }
    // Clear queue only after all batches are sent successfully
    localStorage.removeItem(QUEUE_KEY);
  } catch {
    // Leave queue intact on failure — will retry on next "online" event
  }
}

// Auto-flush when coming back online
if (typeof window !== "undefined") {
  window.addEventListener("online", flushQueue);
}

// ── Core track function ───────────────────────────────────────────────────────

export async function track(
  eventName: EventName,
  properties: Record<string, unknown> = {}
): Promise<void> {
  if (typeof window === "undefined" || TRACKING_DISABLED || !hasAnalyticsConsent()) return; // SSR/consent guard

  const { page_type, page_id, locale, ...rest } = properties as {
    page_type?: string;
    page_id?: string;
    locale?: string;
    [key: string]: unknown;
  };

  const payload: TrackPayload = {
    event_name: eventName,
    visitor_id: getVisitorId(),
    session_id: getSessionId(),
    page_url: window.location.href,
    page_type,
    page_id: page_id ? String(page_id) : undefined,
    locale: locale || document.documentElement.lang || "en",
    referrer: document.referrer || undefined,
    campaign_id: new URLSearchParams(window.location.search).get("utm_campaign") || undefined,
    properties: Object.keys(rest).length > 0 ? rest : undefined,
    analytics_consent: true,
  };

  try {
    const res = await fetch(EVENTS_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
  } catch {
    // Offline or backend down — queue for retry
    enqueue(payload);
  }

  // Fire GA4 in parallel — does not block or affect first-party tracking
  _fireGA4(eventName, { ...properties, visitor_id: payload.visitor_id });
}

// ── Convenience: page-type shortcuts ─────────────────────────────────────────

export const trackPageView = (props: Record<string, unknown> = {}) =>
  track("page_view", props);

export const trackProductView = (productId: string, extra?: Record<string, unknown>) =>
  track("product_view", { page_type: "product", page_id: productId, ...extra });

export const trackCategoryView = (categoryId: string, extra?: Record<string, unknown>) =>
  track("category_view", { page_type: "category", page_id: categoryId, ...extra });

export const trackApplicationView = (appId: string, extra?: Record<string, unknown>) =>
  track("application_view", { page_type: "application", page_id: appId, ...extra });

export const trackComparisonView = (comparisonId: string, extra?: Record<string, unknown>) =>
  track("comparison_view", { page_type: "comparison", page_id: comparisonId, ...extra });

export const trackFAQExpand = (faqId: string) =>
  track("faq_expand", { page_type: "faq", page_id: faqId });

export const trackSpecDownload = (productId: string, fileName: string) =>
  track("spec_download", { page_type: "product", page_id: productId, file_name: fileName });

export const trackCTAClick = (ctaLabel: string, targetUrl: string) =>
  track("cta_click", { cta_label: ctaLabel, target_url: targetUrl });

export const trackFormStart = (formType: "rfq" | "contact") =>
  track("form_start", { form_type: formType });

export const trackFormSubmit = (formType: "rfq" | "contact") =>
  track("form_submit", { form_type: formType });

export const trackRFQStart = () => track("rfq_start", { page_type: "rfq" });

export const trackRFQSubmit = () => track("rfq_submit", { page_type: "rfq" });

export const trackCertificationView = (certId: string) =>
  track("certification_view", { page_type: "certification", page_id: certId });
