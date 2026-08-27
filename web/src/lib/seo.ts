import type { Metadata } from "next";
import { siteConfig, type SiteConfig } from "@/lib/siteConfig";
import { PUBLIC_LOCALES } from "@/i18n/routing";
import { toRouteLocale } from "@/lib/contentLocale";

export function getSiteUrl(config: SiteConfig = siteConfig) {
  return config.siteUrl;
}

export function buildCanonicalUrl(path: string, locale?: string, config: SiteConfig = siteConfig) {
  const siteUrl = getSiteUrl(config);
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const routeLocale = toRouteLocale(locale);
  const localePrefix = routeLocale !== "en" ? `/${routeLocale}` : "";
  return `${siteUrl}${localePrefix}${cleanPath}`;
}

export function buildLocaleAlternates(
  path: string,
  locales: Array<{ locale: string }> = [],
  config: SiteConfig = siteConfig,
): Record<string, string> | undefined {
  const canonical = buildCanonicalUrl(path, undefined, config);
  const languages: Record<string, string> = { "x-default": canonical, en: canonical };
  for (const variant of locales) {
    const routeLocale = toRouteLocale(variant.locale);
    languages[routeLocale] = buildCanonicalUrl(path, routeLocale, config);
  }
  return Object.keys(languages).length > 2 ? languages : undefined;
}

export function buildDefaultMetadata(input?: Partial<Metadata>, config: SiteConfig = siteConfig): Metadata {
  const siteName = config.brandName;
  const siteUrl = getSiteUrl(config);
  return {
    metadataBase: new URL(siteUrl),
    title: {
      default: siteName,
      template: `%s | ${siteName}`,
    },
    description: "外銷製造商官網成長系統",
    alternates: {
      canonical: siteUrl,
    },
    openGraph: {
      type: "website",
      url: siteUrl,
      siteName,
      title: siteName,
      description: "外銷製造商官網成長系統",
    },
    twitter: {
      card: "summary_large_image",
      site: process.env.NEXT_PUBLIC_TWITTER_HANDLE ?? undefined,
      title: siteName,
      description: "外銷製造商官網成長系統",
    },
    robots: {
      index: true,
      follow: true,
    },
    ...input,
  };
}

/**
 * Build Twitter card metadata for a specific page.
 * Merges with the caller's existing openGraph images so we don't duplicate data.
 */
export function buildTwitterMeta(opts: {
  title: string;
  description?: string;
  imageUrl?: string | null;
}): Metadata["twitter"] {
  return {
    card: "summary_large_image",
    site: process.env.NEXT_PUBLIC_TWITTER_HANDLE ?? undefined,
    title: opts.title,
    description: opts.description ?? undefined,
    images: opts.imageUrl ? [opts.imageUrl] : undefined,
  };
}

export function buildCoreLocaleAlternates(path: string, config: SiteConfig = siteConfig): Record<string, string> {
  const english = buildCanonicalUrl(path, "en", config);
  return Object.fromEntries([
    ["x-default", english],
    ...PUBLIC_LOCALES.map((locale) => [locale, buildCanonicalUrl(path, locale, config)]),
  ]);
}

const OPEN_GRAPH_LOCALES: Record<string, string> = {
  en: "en_US",
  "zh-TW": "zh_TW",
  ja: "ja_JP",
  fr: "fr_FR",
  ru: "ru_RU",
};

export function buildLocalizedMetadata(
  base: Metadata,
  path: string,
  locale: string,
  config: SiteConfig = siteConfig,
): Metadata {
  const canonical = buildCanonicalUrl(path, locale, config);
  const title = typeof base.title === "string" && base.title.toLocaleLowerCase().includes(config.brandName.toLocaleLowerCase())
    ? { absolute: base.title }
    : base.title;
  return {
    ...base,
    title,
    alternates: { ...base.alternates, canonical, languages: buildCoreLocaleAlternates(path, config) },
    openGraph: { ...base.openGraph, url: canonical, locale: OPEN_GRAPH_LOCALES[toRouteLocale(locale)] ?? "en_US" },
  };
}
