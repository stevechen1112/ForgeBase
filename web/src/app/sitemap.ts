import type { MetadataRoute } from "next";
import {
  getAllPublishedApplications,
  getAllPublishedProducts,
  getPublishedCapabilities,
  getPublishedCategories,
  getPublishedCertifications,
  getPublishedComparisons,
  getPublishedFAQs,
} from "@/lib/api";
import { PUBLIC_LOCALES, type Locale } from "@/i18n/routing";
import { toContentLocale } from "@/lib/contentLocale";
import { localizedPath } from "@/lib/localizedPath";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

type Entry = MetadataRoute.Sitemap[number];
type RouteRecord = {
  key: string;
  locale: Locale;
  path: string;
  lastModified: Date;
  changeFrequency: Entry["changeFrequency"];
  priority: number;
};

function isPublishedForRoute(itemLocale: string, routeLocale: Locale): boolean {
  return toContentLocale(itemLocale) === toContentLocale(routeLocale);
}

function toEntries(siteUrl: string, records: RouteRecord[]): Entry[] {
  const groups = new Map<string, RouteRecord[]>();
  for (const record of records) {
    groups.set(record.key, [...(groups.get(record.key) ?? []), record]);
  }

  return records.map((record) => {
    const variants = groups.get(record.key) ?? [record];
    const languages: Record<string, string> = Object.fromEntries(
      variants.map((variant) => [
        variant.locale,
        `${siteUrl}${localizedPath(variant.locale, variant.path)}`,
      ]),
    );
    if (languages.en) languages["x-default"] = languages.en;
    return {
      url: `${siteUrl}${localizedPath(record.locale, record.path)}`,
      lastModified: record.lastModified,
      changeFrequency: record.changeFrequency,
      priority: record.priority,
      alternates: Object.keys(languages).length > 1 ? { languages } : undefined,
    };
  });
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { siteUrl } = await getRuntimeSiteContext();
  const now = new Date();
  const localeData = await Promise.all(PUBLIC_LOCALES.map(async (locale) => {
    const [categories, products, applications, capabilities, certifications, comparisons, faqs] = await Promise.all([
      getPublishedCategories(locale),
      getAllPublishedProducts(locale, 1, 100),
      getAllPublishedApplications(locale, 1, 100),
      getPublishedCapabilities(locale),
      getPublishedCertifications(locale),
      getPublishedComparisons(locale),
      getPublishedFAQs(locale),
    ]);
    return {
      locale,
      categories: categories.filter((item) => isPublishedForRoute(item.locale, locale)),
      products: products.data.filter((item) => isPublishedForRoute(item.locale, locale)),
      applications: applications.data.filter((item) => isPublishedForRoute(item.locale, locale)),
      capabilities: capabilities.filter((item) => isPublishedForRoute(item.locale, locale)),
      certifications: certifications.filter((item) => isPublishedForRoute(item.locale, locale)),
      comparisons: comparisons.filter((item) => isPublishedForRoute(item.locale, locale)),
      faqs: faqs.filter((item) => isPublishedForRoute(item.locale, locale)),
    };
  }));

  const staticRoutes = [
    ["/", 1, "weekly"],
    ["/products", 0.9, "weekly"],
    ["/applications", 0.8, "weekly"],
    ["/certifications", 0.6, "monthly"],
    ["/capabilities", 0.6, "monthly"],
    ["/faq", 0.6, "monthly"],
    ["/comparisons", 0.6, "monthly"],
    ["/rfq", 0.5, "yearly"],
    ["/about", 0.5, "monthly"],
    ["/contact", 0.5, "yearly"],
    ["/docs", 0.4, "monthly"],
    ["/news", 0.4, "monthly"],
    ["/careers", 0.3, "monthly"],
    ["/dealers", 0.3, "monthly"],
    ["/privacy", 0.3, "yearly"],
    ["/terms", 0.3, "yearly"],
    ["/cookies", 0.3, "yearly"],
  ] as const;
  const records: RouteRecord[] = staticRoutes.flatMap(([path, priority, changeFrequency]) =>
    PUBLIC_LOCALES.map((locale) => ({
      key: `static:${path}`,
      locale,
      path,
      lastModified: now,
      changeFrequency,
      priority: locale === "en" ? priority : Math.max(0.1, priority - 0.1),
    })),
  );

  for (const data of localeData) {
    const categoryById = new Map(data.categories.map((category) => [category.id, category.slug]));
    records.push(...data.categories.map((category) => ({
      key: `category:${category.slug}`,
      locale: data.locale,
      path: `/products/${category.slug}`,
      lastModified: now,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })));
    records.push(...data.products.flatMap((product) => {
      const categorySlug = categoryById.get(product.category_id);
      if (!categorySlug) return [];
      return [{
        key: `product:${product.slug}`,
        locale: data.locale,
        path: `/products/${categorySlug}/${product.slug}`,
        lastModified: product.published_at ? new Date(product.published_at) : now,
        changeFrequency: "monthly" as const,
        priority: 0.7,
      }];
    }));
    records.push(...data.applications.map((application) => ({
      key: `application:${application.slug}`,
      locale: data.locale,
      path: `/applications/${application.slug}`,
      lastModified: application.published_at ? new Date(application.published_at) : now,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })));
    records.push(...data.capabilities.map((capability) => ({
      key: `capability:${capability.slug}`,
      locale: data.locale,
      path: `/capabilities/${capability.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })));
    records.push(...data.certifications.map((certification) => ({
      key: `certification:${certification.slug}`,
      locale: data.locale,
      path: `/certifications/${certification.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })));
    records.push(...data.comparisons.map((comparison) => ({
      key: `comparison:${comparison.slug}`,
      locale: data.locale,
      path: `/comparisons/${comparison.slug}`,
      lastModified: now,
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })));
    const faqTags = [...new Set(data.faqs.map((item) => item.category_tag).filter(Boolean))];
    records.push(...faqTags.map((tag) => {
      const slug = String(tag).toLowerCase().replace(/\s+/g, "-");
      return {
        key: `faq:${slug}`,
        locale: data.locale,
        path: `/faq/${encodeURIComponent(slug)}`,
        lastModified: now,
        changeFrequency: "monthly" as const,
        priority: 0.5,
      };
    }));
  }

  return toEntries(siteUrl, records);
}
