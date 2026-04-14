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

export type LocalizedText = string | Partial<Record<string, string>>;

export type SiteNavItem = {
  href: string;
  label?: LocalizedText;
};

export type SiteAction = {
  href: string;
  label: LocalizedText;
};

export type SiteFooterSection = {
  heading: LocalizedText;
  items: SiteNavItem[];
};

export type SiteSocialLink = {
  href: string;
  label: LocalizedText;
  platform?: string;
};

export type SiteFooterCta = {
  title: LocalizedText;
  description?: LocalizedText;
  action: SiteAction;
};

export type SiteAssetManifest = {
  homeHero?: string;
  aboutHero?: string;
  productsHero?: string;
  qualityInspection?: string;
  customPackaging?: string;
  categoryBySlug?: Record<string, string>;
  applicationBySlug?: Record<string, string>;
  productByKey?: Record<string, string>;
};
const LAYOUT_VARIANTS: LayoutVariant[] = ["classic", "industrial"];
const THEME_KEYS: ThemeKey[] = ["cobalt", "forest", "slate", "warm", "industrial"];

export interface SiteConfig {
  brandName: string;
  logoMark: string;
  siteUrl: string;
  contactEmail: string;
  careersEmail: string;
  contactPhone: string;
  assetBase: string;
  demoCompanyFolder: string;
  theme: ThemeKey;
  layout: LayoutVariant;
  headerNav?: SiteNavItem[];
  headerActions?: SiteAction[];
  footerSections?: SiteFooterSection[];
  footerBadges?: LocalizedText[];
  socialLinks?: SiteSocialLink[];
  footerCta?: SiteFooterCta | null;
  assetManifest?: SiteAssetManifest;
}

export function resolveLocalizedText(value: LocalizedText | undefined, locale: string, fallback = ""): string {
  if (!value) {
    return fallback;
  }
  if (typeof value === "string") {
    return value;
  }
  return value[locale] ?? value.en ?? value["zh-TW"] ?? fallback;
}

export function normalizeThemeKey(raw?: string | null): ThemeKey {
  if (raw && THEME_KEYS.includes(raw as ThemeKey)) {
    return raw as ThemeKey;
  }
  return "cobalt";
}

export function getThemeKey(): ThemeKey {
  return normalizeThemeKey(process.env.NEXT_PUBLIC_THEME ?? "cobalt");
}

/** Map theme keys to their layout variant */
const LAYOUT_MAP: Record<ThemeKey, LayoutVariant> = {
  cobalt: "classic",
  forest: "classic",
  slate: "classic",
  warm: "classic",
  industrial: "industrial",
};

export function normalizeLayoutVariant(raw?: string | null, theme: ThemeKey = getThemeKey()): LayoutVariant {
  if (raw && LAYOUT_VARIANTS.includes(raw as LayoutVariant)) {
    return raw as LayoutVariant;
  }
  return LAYOUT_MAP[theme];
}

export function getLayoutVariant(theme: ThemeKey = getThemeKey()): LayoutVariant {
  return normalizeLayoutVariant(process.env.NEXT_PUBLIC_LAYOUT, theme);
}

// ── Brand identity ─────────────────────────────────────────────────
export const siteConfig: SiteConfig = {
  /** Display brand name — MUST be set via NEXT_PUBLIC_SITE_NAME */
  brandName: process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase",

  /** Short logo mark shown inside the header/footer icon */
  logoMark: process.env.NEXT_PUBLIC_LOGO_MARK || "FB",

  /** Canonical site URL without trailing slash */
  siteUrl: (process.env.NEXT_PUBLIC_SITE_URL || "https://example.com").replace(/\/$/, ""),

  /** Contact email — MUST be set via NEXT_PUBLIC_CONTACT_EMAIL */
  contactEmail: process.env.NEXT_PUBLIC_CONTACT_EMAIL || "hello@forgebase.co",

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
  layout: getLayoutVariant(),

  /** Optional tenant-configurable header/footer structure */
  headerNav: undefined,
  headerActions: undefined,
  footerSections: undefined,
  footerBadges: undefined,
  socialLinks: undefined,
  footerCta: undefined,

  /** Default asset manifest keeps the existing demo experience as a legacy fallback. */
  assetManifest: {
    homeHero: `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/homepage-hero-manufacturer.png`,
    aboutHero: `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/about-factory-hero.png`,
    productsHero: `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-toolkits-storage-hero.png`,
    qualityInspection: `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/capability-quality-inspection.png`,
    customPackaging: `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/capability-custom-packaging-oem.png`,
    categoryBySlug: {
      "torque-and-socket-tools": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-torque-socket-tools-hero.png`,
      "insulated-electrical-tools": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-insulated-electrical-tools-hero.png`,
      "striking-and-workshop-tools": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-striking-workshop-tools-hero.png`,
      "automotive-service-tools": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-automotive-service-tools-hero.png`,
      "custom-toolkits-and-storage": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/category-toolkits-storage-hero.png`,
    },
    applicationBySlug: {
      "automotive-aftermarket-service": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-automotive-aftermarket-service.png`,
      "industrial-maintenance-and-mro": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-industrial-maintenance-mro.png`,
      "electrical-installation-and-utility-work": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-electrical-installation-utility.png`,
      "workshop-assembly-and-repair": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-workshop-assembly-repair.png`,
      "private-label-tool-programs": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-private-label-programs.png`,
      "field-service-and-mobile-maintenance": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/application-field-service-mobile.png`,
    },
    productByKey: {
      "NFT-TW250": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-tw250-main.png`,
      "NFT-TW380": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-tw380-main.png`,
      "NFT-TW500": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-tw500-main.png`,
      "NFT-TWA120": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-twa120-main.png`,
      "NFT-RH372": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-rh372-main.png`,
      "NFT-RH390F": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-rh390f-main.png`,
      "NFT-SS094": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ss094-main.png`,
      "NFT-SS137": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ss137-main.png`,
      "NFT-ID006": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-id006-main.png`,
      "NFT-ID013": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-id013-main.png`,
      "NFT-IP200": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ip200-main.png`,
      "NFT-IP160N": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ip160n-main.png`,
      "NFT-IP165D": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ip165d-main.png`,
      "NFT-EK018": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ek018-main.png`,
      "NFT-DH045": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-dh045-main.png`,
      "NFT-DH060": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-dh060-main.png`,
      "NFT-SM40": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-sm40-main.png`,
      "NFT-EH24": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-eh24-main.png`,
      "NFT-PB4S": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-pb4s-main.png`,
      "NFT-CS6P": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-cs6p-main.png`,
      "NFT-AM12F": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-am12f-main.png`,
      "NFT-AMBC7": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ambc7-main.png`,
      "NFT-AMSP5": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-amsp5-main.png`,
      "NFT-AMPU3": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ampu3-main.png`,
      "NFT-AMHTM": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-amhtm-main.png`,
      "NFT-AMTR8": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-amtr8-main.png`,
      "NFT-KTMEV1": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktmev1-main.png`,
      "NFT-KTBC89": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktbc89-main.png`,
      "NFT-KTEC24": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktec24-main.png`,
      "NFT-KTWS128": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktws128-main.png`,
      "NFT-KTPLR56": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktplr56-main.png`,
      "NFT-KTFM42": `${process.env.NEXT_PUBLIC_ASSET_BASE || "/demo/handtool-company/assets"}/generated/product-nft-ktfm42-main.png`,
    },
  },
};
