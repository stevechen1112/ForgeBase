import "server-only";

import { cache } from "react";
import {
  siteConfig,
  type SiteConfig,
  type SiteNavItem,
  type SiteAction,
  type SiteFooterSection,
  type LocalizedText,
  type SiteSocialLink,
  type SiteFooterCta,
  type SiteAssetManifest,
  normalizeLayoutVariant,
  normalizeThemeKey,
} from "@/lib/siteConfig";
import { tenantCacheTag, withRequestTenantHeaders } from "@/lib/serverTenant";
import { rewriteLegacyPublicPath } from "@/lib/legacyPublicPaths";

export type RuntimeSiteContext = {
  siteConfig: SiteConfig;
  siteUrl: string;
  siteName: string;
  contactEmail: string;
  contactPhone: string;
  careersEmail: string;
  isIndustrial: boolean;
  isPrecision: boolean;
};

type SiteProfileResponse = {
  brand_name?: string | null;
  logo_mark?: string | null;
  logo_url?: string | null;
  favicon_url?: string | null;
  theme_key?: string | null;
  layout_key?: string | null;
  contact_email?: string | null;
  contact_phone?: string | null;
  site_url?: string | null;
  default_locale?: string | null;
  asset_base?: string | null;
  demo_company_folder?: string | null;
  header_nav_json?: string | null;
  header_actions_json?: string | null;
  footer_sections_json?: string | null;
  footer_badges_json?: string | null;
  social_links_json?: string | null;
  footer_cta_title?: string | null;
  footer_cta_description?: string | null;
  footer_cta_label?: string | null;
  footer_cta_href?: string | null;
  asset_manifest_json?: string | null;
  site_copy_json?: string | null;
};

const API_BASE =
  process.env.API_INTERNAL_URL ||
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function normalizeString(value?: string | null): string | undefined {
  const normalized = value?.trim();
  return normalized ? normalized : undefined;
}

function normalizeSiteUrl(value?: string | null): string | undefined {
  const normalized = normalizeString(value);
  return normalized ? normalized.replace(/\/$/, "") : undefined;
}

function parseJsonField<T>(value?: string | null): T | undefined {
  if (!value) {
    return undefined;
  }

  try {
    return JSON.parse(value) as T;
  } catch {
    return undefined;
  }
}

function normalizeLocalizedText(value: unknown): LocalizedText | undefined {
  if (typeof value === "string") {
    return value;
  }
  if (value && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).filter(([, item]) => typeof item === "string");
    return entries.length ? (Object.fromEntries(entries) as Partial<Record<string, string>>) : undefined;
  }
  return undefined;
}

function normalizeNavItems(value?: unknown): SiteNavItem[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const items: SiteNavItem[] = [];
  for (const item of value) {
    if (!item || typeof item !== "object") {
      continue;
    }
    const href = normalizeString((item as { href?: string }).href);
    if (!href) {
      continue;
    }
    items.push({
      href: rewriteLegacyPublicPath(href),
      label: normalizeLocalizedText((item as { label?: unknown }).label),
    });
  }
  return items.length ? items : undefined;
}

function normalizeActions(value?: unknown): SiteAction[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const items: SiteAction[] = value
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const href = normalizeString((item as { href?: string }).href);
      const label = normalizeLocalizedText((item as { label?: unknown }).label);
      if (!href || !label) {
        return null;
      }
      return { href: rewriteLegacyPublicPath(href), label } satisfies SiteAction;
    })
    .filter((item): item is SiteAction => Boolean(item));
  return items.length ? items : undefined;
}

function normalizeFooterSections(value?: unknown): SiteFooterSection[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const sections: SiteFooterSection[] = value
    .map((section) => {
      if (!section || typeof section !== "object") {
        return null;
      }
      const heading = normalizeLocalizedText((section as { heading?: unknown }).heading);
      const items = normalizeNavItems((section as { items?: unknown }).items);
      if (!heading || !items?.length) {
        return null;
      }
      return { heading, items } satisfies SiteFooterSection;
    })
    .filter((item): item is SiteFooterSection => Boolean(item));
  return sections.length ? sections : undefined;
}

function normalizeLocalizedList(value?: unknown): LocalizedText[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const items = value.map(normalizeLocalizedText).filter((item): item is LocalizedText => Boolean(item));
  return items.length ? items : undefined;
}

function normalizeSocialLinks(value?: unknown): SiteSocialLink[] | undefined {
  if (!Array.isArray(value)) {
    return undefined;
  }
  const items: SiteSocialLink[] = value
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const href = normalizeString((item as { href?: string }).href);
      const label = normalizeLocalizedText((item as { label?: unknown }).label);
      const platform = normalizeString((item as { platform?: string }).platform);
      if (!href || !label) {
        return null;
      }
      return {
        href,
        label,
        ...(platform ? { platform } : {}),
      } satisfies SiteSocialLink;
    })
    .filter((item): item is SiteSocialLink => item !== null);
  return items.length ? items : undefined;
}

function normalizeFooterCta(profile: SiteProfileResponse): SiteFooterCta | undefined {
  const title = normalizeLocalizedText(profile.footer_cta_title);
  const label = normalizeLocalizedText(profile.footer_cta_label);
  const href = normalizeString(profile.footer_cta_href);
  if (!title || !label || !href) {
    return undefined;
  }
  return {
    title,
    description: normalizeLocalizedText(profile.footer_cta_description),
    action: { label, href: rewriteLegacyPublicPath(href) },
  };
}

function mergeAssetManifest(
  fallback?: SiteAssetManifest,
  incoming?: SiteAssetManifest,
): SiteAssetManifest | undefined {
  if (!incoming) return fallback;
  if (!fallback) return incoming;
  return {
    homeHero: incoming.homeHero || fallback.homeHero,
    aboutHero: incoming.aboutHero || fallback.aboutHero,
    productsHero: incoming.productsHero || fallback.productsHero,
    qualityInspection: incoming.qualityInspection || fallback.qualityInspection,
    customPackaging: incoming.customPackaging || fallback.customPackaging,
    categoryBySlug: incoming.categoryBySlug ?? fallback.categoryBySlug,
    applicationBySlug: incoming.applicationBySlug ?? fallback.applicationBySlug,
    productByKey: incoming.productByKey ?? fallback.productByKey,
  };
}

function normalizeAssetManifest(value?: unknown): SiteAssetManifest | undefined {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const manifest = value as Record<string, unknown>;
  const normalizeMap = (mapValue: unknown): Record<string, string> | undefined => {
    if (!mapValue || typeof mapValue !== "object") {
      return undefined;
    }
    const entries = Object.entries(mapValue as Record<string, unknown>).filter(([, item]) => typeof item === "string");
    return entries.length ? Object.fromEntries(entries) as Record<string, string> : undefined;
  };

  return {
    homeHero: normalizeString(manifest.homeHero as string | undefined),
    aboutHero: normalizeString(manifest.aboutHero as string | undefined),
    productsHero: normalizeString(manifest.productsHero as string | undefined),
    qualityInspection: normalizeString(manifest.qualityInspection as string | undefined),
    customPackaging: normalizeString(manifest.customPackaging as string | undefined),
    categoryBySlug: normalizeMap(manifest.categoryBySlug),
    applicationBySlug: normalizeMap(manifest.applicationBySlug),
    productByKey: normalizeMap(manifest.productByKey),
  };
}

export const getRuntimeSiteConfig = cache(async (): Promise<SiteConfig> => {
  const fallback: SiteConfig = { ...siteConfig };

  try {
    const tenantRequest = await withRequestTenantHeaders({ Accept: "application/json" });
    const response = await fetch(`${API_BASE}/api/v1/site-profile`, {
      headers: tenantRequest.headers,
      next: { revalidate: 60, tags: [tenantCacheTag(tenantRequest.host)] },
    });

    if (!response.ok) {
      return fallback;
    }

    const profile = (await response.json()) as SiteProfileResponse;
    const theme = normalizeThemeKey(profile.theme_key);

    return {
      ...fallback,
      brandName: normalizeString(profile.brand_name) ?? fallback.brandName,
      logoMark: normalizeString(profile.logo_mark) ?? fallback.logoMark,
      logoUrl: normalizeString(profile.logo_url) ?? fallback.logoUrl,
      hiddenBlocks: parseJsonField<{ hiddenBlocks?: SiteConfig["hiddenBlocks"] }>(profile.site_copy_json)?.hiddenBlocks ?? fallback.hiddenBlocks,
      siteUrl: normalizeSiteUrl(profile.site_url) ?? fallback.siteUrl,
      contactEmail: normalizeString(profile.contact_email) ?? fallback.contactEmail,
      contactPhone: normalizeString(profile.contact_phone) ?? fallback.contactPhone,
      assetBase: normalizeString(profile.asset_base) ?? fallback.assetBase,
      demoCompanyFolder: normalizeString(profile.demo_company_folder) ?? fallback.demoCompanyFolder,
      theme,
      layout: normalizeLayoutVariant(profile.layout_key, theme),
      headerNav: normalizeNavItems(parseJsonField(profile.header_nav_json)) ?? fallback.headerNav,
      headerActions: normalizeActions(parseJsonField(profile.header_actions_json)) ?? fallback.headerActions,
      footerSections: normalizeFooterSections(parseJsonField(profile.footer_sections_json)) ?? fallback.footerSections,
      footerBadges: normalizeLocalizedList(parseJsonField(profile.footer_badges_json)) ?? fallback.footerBadges,
      socialLinks: normalizeSocialLinks(parseJsonField(profile.social_links_json)) ?? fallback.socialLinks,
      footerCta: normalizeFooterCta(profile) ?? fallback.footerCta,
      assetManifest: mergeAssetManifest(
        fallback.assetManifest,
        normalizeAssetManifest(parseJsonField(profile.asset_manifest_json)),
      ),
      siteCopy: parseJsonField<Record<string, unknown>>(profile.site_copy_json),
    };
  } catch {
    return fallback;
  }
});

export const getRuntimeSiteContext = cache(async (): Promise<RuntimeSiteContext> => {
  const runtimeSiteConfig = await getRuntimeSiteConfig();

  return {
    siteConfig: runtimeSiteConfig,
    siteUrl: runtimeSiteConfig.siteUrl,
    siteName: runtimeSiteConfig.brandName,
    contactEmail: runtimeSiteConfig.contactEmail,
    contactPhone: runtimeSiteConfig.contactPhone,
    careersEmail: runtimeSiteConfig.careersEmail,
    isIndustrial: runtimeSiteConfig.layout === "industrial" || runtimeSiteConfig.layout === "precision",
    isPrecision: runtimeSiteConfig.layout === "precision",
  };
});
