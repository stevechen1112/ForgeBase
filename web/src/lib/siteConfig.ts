/**
 * Centralised site / brand configuration.
 *
 * Every page should read brand name, contact info, logo, and asset paths
 * from here instead of inlining `process.env.NEXT_PUBLIC_SITE_NAME` checks.
 *
 * When multi-theme support lands this will be the single place that resolves
 * the active theme key and brand tokens.
 */

// ── Theme key ──────────────────────────────────────────────────────
export type ThemeKey = "cobalt" | "forest" | "slate" | "warm" | "industrial";

/**
 * Layout variant driven by the active theme.
 * - "classic"     — rounded cards, centered headings, light hero
 * - "industrial"  — angular cards, left-aligned headings, dark header, bold typography
 */
export type LayoutVariant = "classic" | "industrial";

export function getThemeKey(): ThemeKey {
  const raw = process.env.NEXT_PUBLIC_THEME ?? "cobalt";
  if (["cobalt", "forest", "slate", "warm", "industrial"].includes(raw)) return raw as ThemeKey;
  return "cobalt";
}

/** Map theme keys to their layout variant */
const LAYOUT_MAP: Record<ThemeKey, LayoutVariant> = {
  cobalt: "classic",
  forest: "classic",
  slate: "classic",
  warm: "classic",
  industrial: "industrial",
};

// ── Brand identity ─────────────────────────────────────────────────
export const siteConfig = {
  /** Display brand name — MUST be set via NEXT_PUBLIC_SITE_NAME */
  brandName: process.env.NEXT_PUBLIC_SITE_NAME || "",

  /** Short logo mark shown inside the header/footer icon */
  logoMark: process.env.NEXT_PUBLIC_LOGO_MARK || "",

  /** Canonical site URL without trailing slash */
  siteUrl: (process.env.NEXT_PUBLIC_SITE_URL || "https://example.com").replace(/\/$/, ""),

  /** Contact email — MUST be set via NEXT_PUBLIC_CONTACT_EMAIL */
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "",

  /** Careers / HR contact email */
  careersEmail: process.env.NEXT_PUBLIC_CAREERS_EMAIL || process.env.NEXT_PUBLIC_CONTACT_EMAIL || "",

  /** Primary contact phone */
  contactPhone: process.env.NEXT_PUBLIC_CONTACT_PHONE || "+886-4-3700-2218",

  /** Base path for demo/generated assets (no trailing slash) */
  assetBase: process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets",

  /** Demo company folder name (for file-system asset resolution) */
  demoCompanyFolder: process.env.NEXT_PUBLIC_DEMO_COMPANY || "handtool-company",

  /** Active theme key */
  theme: getThemeKey(),

  /** Layout variant — determines which component set is used */
  layout: LAYOUT_MAP[getThemeKey()],
} as const;
