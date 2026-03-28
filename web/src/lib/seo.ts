import type { Metadata } from "next";

export function getSiteUrl() {
  return (process.env.NEXT_PUBLIC_SITE_URL || "https://example.com").replace(/\/$/, "");
}

export function buildCanonicalUrl(path: string, locale?: string) {
  const siteUrl = getSiteUrl();
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  const localePrefix = locale && locale !== "en" ? `/${locale}` : "";
  return `${siteUrl}${localePrefix}${cleanPath}`;
}

export function buildLocaleAlternates(
  path: string,
  locales: Array<{ locale: string }> = [],
): Record<string, string> | undefined {
  const canonical = buildCanonicalUrl(path);
  const languages: Record<string, string> = { "x-default": canonical, en: canonical };
  for (const variant of locales) {
    languages[variant.locale] = buildCanonicalUrl(path, variant.locale);
  }
  return Object.keys(languages).length > 2 ? languages : undefined;
}

export function buildDefaultMetadata(input?: Partial<Metadata>): Metadata {
  const siteName = process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase";
  const siteUrl = getSiteUrl();
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