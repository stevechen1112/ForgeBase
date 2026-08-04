import type { MetadataRoute } from "next";
import {
  getPublishedCategories,
  getAllPublishedProducts,
  getAllPublishedApplications,
  getPublishedCapabilities,
  getPublishedCertifications,
  getPublishedComparisons,
  getPublishedFAQs,
} from "@/lib/api";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const { siteUrl: SITE_URL } = await getRuntimeSiteContext();
  const now = new Date();

  // Fetch ALL published content across all locales — paginate to capture all items
  const MAX_SITEMAP_ITEMS = 5000;
  const [categories, productsRes, applicationsRes, capabilities, certifications, comparisons, faqs] = await Promise.all([
    getPublishedCategories(),
    getAllPublishedProducts("en", 1, MAX_SITEMAP_ITEMS),
    getAllPublishedApplications("en", 1, MAX_SITEMAP_ITEMS),
    getPublishedCapabilities(),
    getPublishedCertifications(),
    getPublishedComparisons(),
    getPublishedFAQs(),
  ]);

  const staticRoutes: MetadataRoute.Sitemap = [
    { url: SITE_URL, lastModified: now, changeFrequency: "weekly", priority: 1.0 },
    { url: `${SITE_URL}/products`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE_URL}/applications`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE_URL}/certifications`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE_URL}/capabilities`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE_URL}/faq`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE_URL}/comparisons`, lastModified: now, changeFrequency: "monthly", priority: 0.6 },
    { url: `${SITE_URL}/request-quote`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
    { url: `${SITE_URL}/rfq`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
    { url: `${SITE_URL}/about`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/contact`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
    { url: `${SITE_URL}/news`, lastModified: now, changeFrequency: "weekly", priority: 0.4 },
    { url: `${SITE_URL}/careers`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${SITE_URL}/docs`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${SITE_URL}/dealers`, lastModified: now, changeFrequency: "monthly", priority: 0.4 },
    { url: `${SITE_URL}/privacy`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/terms`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/cookies`, lastModified: now, changeFrequency: "yearly", priority: 0.3 },
    { url: `${SITE_URL}/zh-TW`, lastModified: now, changeFrequency: "weekly", priority: 0.9 },
    { url: `${SITE_URL}/zh-TW/products`, lastModified: now, changeFrequency: "weekly", priority: 0.8 },
    { url: `${SITE_URL}/zh-TW/applications`, lastModified: now, changeFrequency: "weekly", priority: 0.7 },
    { url: `${SITE_URL}/zh-TW/certifications`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/zh-TW/about`, lastModified: now, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/zh-TW/contact`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
    { url: `${SITE_URL}/zh-TW/rfq`, lastModified: now, changeFrequency: "yearly", priority: 0.5 },
  ];

  const categoryRoutes: MetadataRoute.Sitemap = categories.map((cat) => ({
    url: `${SITE_URL}/products/${cat.slug}`,
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  // Products: en → /products/{catSlug}/{slug}
  //           others → /{locale}/products/{catSlug}/{slug}
  const productRoutes: MetadataRoute.Sitemap = productsRes.data.map((product) => {
    const cat = categories.find((c) => c.id === product.category_id);
    const catSlug = cat?.slug ?? "uncategorised";
    const localeMod = product.locale && product.locale !== "en"
      ? `/${product.locale}`
      : "";
    return {
      url: `${SITE_URL}${localeMod}/products/${catSlug}/${product.slug}`,
      lastModified: product.published_at ? new Date(product.published_at) : now,
      changeFrequency: "monthly",
      priority: 0.7,
    };
  });

  // Applications: en → /applications/{slug}
  //               others → /{locale}/applications/{slug}
  const applicationRoutes: MetadataRoute.Sitemap = applicationsRes.data.map((app) => {
    const localeMod = app.locale && app.locale !== "en" ? `/${app.locale}` : "";
    return {
      url: `${SITE_URL}${localeMod}/applications/${app.slug}`,
      lastModified: app.published_at ? new Date(app.published_at) : now,
      changeFrequency: "monthly",
      priority: 0.7,
    };
  });

  const capabilityRoutes: MetadataRoute.Sitemap = capabilities.map((cap) => ({
    url: `${SITE_URL}/capabilities/${cap.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const certificationRoutes: MetadataRoute.Sitemap = certifications.map((cert) => ({
    url: `${SITE_URL}/certifications/${cert.slug}`,
    lastModified: cert.expires_at ? new Date(cert.expires_at) : now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const comparisonRoutes: MetadataRoute.Sitemap = comparisons.map((topic) => ({
    url: `${SITE_URL}/comparisons/${topic.slug}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.6,
  }));

  const faqTagRoutes: MetadataRoute.Sitemap = [...new Set(faqs.map((faq) => faq.category_tag).filter(Boolean))].map((tag) => ({
    url: `${SITE_URL}/faq/${encodeURIComponent(String(tag).toLowerCase().replace(/\s+/g, "-"))}`,
    lastModified: now,
    changeFrequency: "monthly",
    priority: 0.5,
  }));

  return [
    ...staticRoutes,
    ...categoryRoutes,
    ...productRoutes,
    ...applicationRoutes,
    ...capabilityRoutes,
    ...certificationRoutes,
    ...comparisonRoutes,
    ...faqTagRoutes,
  ];
}
