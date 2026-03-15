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
    robots: {
      index: true,
      follow: true,
    },
    ...input,
  };
}