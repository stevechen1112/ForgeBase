import type { MetadataRoute } from "next";
import {
  getPublishedCategories, getAllPublishedProducts, getAllPublishedApplications,
  getPublishedCapabilities, getPublishedCertifications, getPublishedComparisons, getPublishedFAQs,
} from "@/lib/api";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

type Entry = MetadataRoute.Sitemap[number];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { siteUrl } = await getRuntimeSiteContext();
  const now = new Date();
  const [enCategories, zhCategoriesRaw, enProducts, zhProductsRaw, enApps, zhAppsRaw, capabilities, certifications, comparisons, faqs] = await Promise.all([
    getPublishedCategories("en"), getPublishedCategories("zh-TW"),
    getAllPublishedProducts("en", 1, 100), getAllPublishedProducts("zh-TW", 1, 100),
    getAllPublishedApplications("en", 1, 100), getAllPublishedApplications("zh-TW", 1, 100),
    getPublishedCapabilities("en"), getPublishedCertifications("en"), getPublishedComparisons("en"), getPublishedFAQs("en"),
  ]);
  const zhCategories = zhCategoriesRaw.filter((item) => item.locale === "zh-TW");
  const zhProducts = zhProductsRaw.data.filter((item) => item.locale === "zh-TW");
  const zhApps = zhAppsRaw.data.filter((item) => item.locale === "zh-TW");

  const localized = (path: string, priority: number, changeFrequency: Entry["changeFrequency"] = "monthly"): Entry[] => {
    const en = `${siteUrl}${path === "/" ? "" : path}`;
    const zh = `${siteUrl}/zh-TW${path === "/" ? "" : path}`;
    const languages = { "x-default": en, en, "zh-TW": zh };
    return [
      { url: en, lastModified: now, changeFrequency, priority, alternates: { languages } },
      { url: zh, lastModified: now, changeFrequency, priority: Math.max(0.1, priority - 0.1), alternates: { languages } },
    ];
  };

  const staticRoutes = [
    ["/", 1, "weekly"], ["/products", .9, "weekly"], ["/applications", .8, "weekly"],
    ["/certifications", .6, "monthly"], ["/capabilities", .6, "monthly"], ["/faq", .6, "monthly"],
    ["/comparisons", .6, "monthly"], ["/rfq", .5, "yearly"], ["/about", .5, "monthly"],
    ["/contact", .5, "yearly"], ["/privacy", .3, "yearly"], ["/terms", .3, "yearly"], ["/cookies", .3, "yearly"],
  ].flatMap(([path, priority, frequency]) => localized(path as string, priority as number, frequency as Entry["changeFrequency"]));

  const categoryRoutes: Entry[] = enCategories.map((category) => ({
    url: `${siteUrl}/products/${category.slug}`, lastModified: now, changeFrequency: "weekly", priority: .8,
  }));
  categoryRoutes.push(...zhCategories.map((category) => ({
    url: `${siteUrl}/zh-TW/products/${category.slug}`, lastModified: now, changeFrequency: "weekly" as const, priority: .7,
  })));

  const productEntry = (product: (typeof enProducts.data)[number], categories: typeof enCategories): Entry => {
    const category = categories.find((item) => item.id === product.category_id);
    const prefix = product.locale === "zh-TW" ? "/zh-TW" : "";
    return { url: `${siteUrl}${prefix}/products/${category?.slug || "uncategorised"}/${product.slug}`, lastModified: product.published_at ? new Date(product.published_at) : now, changeFrequency: "monthly", priority: .7 };
  };
  const productRoutes = [...enProducts.data.map((item) => productEntry(item, enCategories)), ...zhProducts.map((item) => productEntry(item, zhCategories))];
  const appRoutes: Entry[] = [...enApps.data, ...zhApps].map((item) => ({
    url: `${siteUrl}${item.locale === "zh-TW" ? "/zh-TW" : ""}/applications/${item.slug}`,
    lastModified: item.published_at ? new Date(item.published_at) : now, changeFrequency: "monthly", priority: .7,
  }));
  const capabilityRoutes: Entry[] = capabilities.map((item) => ({ url: `${siteUrl}/capabilities/${item.slug}`, lastModified: now, changeFrequency: "monthly", priority: .6 }));
  const certificationRoutes: Entry[] = certifications.map((item) => ({ url: `${siteUrl}/certifications/${item.slug}`, lastModified: item.expires_at ? new Date(item.expires_at) : now, changeFrequency: "monthly", priority: .6 }));
  const comparisonRoutes: Entry[] = comparisons.map((item) => ({ url: `${siteUrl}/comparisons/${item.slug}`, lastModified: now, changeFrequency: "monthly", priority: .6 }));
  const faqRoutes: Entry[] = [...new Set(faqs.map((item) => item.category_tag).filter(Boolean))].map((tag) => ({ url: `${siteUrl}/faq/${encodeURIComponent(String(tag).toLowerCase().replace(/\s+/g, "-"))}`, lastModified: now, changeFrequency: "monthly", priority: .5 }));
  return [...staticRoutes, ...categoryRoutes, ...productRoutes, ...appRoutes, ...capabilityRoutes, ...certificationRoutes, ...comparisonRoutes, ...faqRoutes];
}
