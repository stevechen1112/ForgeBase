import type { Metadata } from "next";
import { siteConfig, type SiteConfig } from "@/lib/siteConfig";

export function getSiteUrl(config: SiteConfig = siteConfig) {
  return config.siteUrl;
}

export function buildCanonicalUrl(path: string, locale?: string, config: SiteConfig = siteConfig) {
  const siteUrl = getSiteUrl(config);
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const localePrefix = locale && locale !== "en" ? `/${locale}` : "";
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
    languages[variant.locale] = buildCanonicalUrl(path, variant.locale, config);
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
  return { "x-default": english, en: english, "zh-TW": buildCanonicalUrl(path, "zh-TW", config) };
}

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
    openGraph: { ...base.openGraph, url: canonical, locale: locale === "zh-TW" ? "zh_TW" : "en_US" },
  };
}
