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
export type ThemeKey = "cobalt" | "forest" | "slate" | "warm";

export function getThemeKey(): ThemeKey {
  const raw = process.env.NEXT_PUBLIC_THEME ?? "cobalt";
  if (["cobalt", "forest", "slate", "warm"].includes(raw)) return raw as ThemeKey;
  return "cobalt";
}

// ── Brand identity ─────────────────────────────────────────────────
function resolveBrandName(): string {
  const env = process.env.NEXT_PUBLIC_SITE_NAME;
  if (!env || env === "ForgeBase") return "NorthForge Tools";
  return env;
}

export const siteConfig = {
  /** Display brand name (e.g. "NorthForge Tools") */
  brandName: resolveBrandName(),

  /** Short logo mark shown inside the header/footer icon */
  logoMark: process.env.NEXT_PUBLIC_LOGO_MARK || "NF",

  /** Canonical site URL without trailing slash */
  siteUrl: (process.env.NEXT_PUBLIC_SITE_URL || "https://example.com").replace(/\/$/, ""),

  /** Contact email */
  contactEmail:
    process.env.NEXT_PUBLIC_CONTACT_EMAIL?.includes("forgebase")
      ? "sales@northforgetools.com"
      : (process.env.NEXT_PUBLIC_CONTACT_EMAIL || "sales@northforgetools.com"),

  /** Primary contact phone */
  contactPhone: process.env.NEXT_PUBLIC_CONTACT_PHONE || "+886-4-3700-2218",

  /** Base path for demo/generated assets (no trailing slash) */
  assetBase: process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets",

  /** Demo company folder name (for file-system asset resolution) */
  demoCompanyFolder: process.env.NEXT_PUBLIC_DEMO_COMPANY || "handtool-company",

  /** Active theme key */
  theme: getThemeKey(),
} as const;
