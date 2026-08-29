/**
 * Server-side API client for fetching content from the FastAPI backend.
 * Used in Next.js Server Components (RSC) — no auth needed for public data.
 */
import type {
  ListResponse,
  ProductCategory,
  Product,
  Application,
  Certification,
  FAQItem,
  CTA,
  Capability,
  ComparisonTopic,
  Page,
} from "@/types/content";
import { tenantCacheTag, withRequestTenantHeaders } from "@/lib/serverTenant";
import {
  mergePublishedListBySlug,
  parseListPage,
  shouldFetchEnglishListFallback,
  withLocaleQuery,
} from "@/lib/localeListFallback";

const BASE = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const DEFAULT_CONTENT_LOCALE = "en";
const STRICT_BUILD_API = process.env.FORGEBASE_STRICT_BUILD_API === "1";

const warnedPaths = new Set<string>();
// Track availability with retry-after logic: cache successes permanently,
// retry failures after RECHECK_MS to avoid permanent process-wide degradation.
let apiAvailableResult: boolean | null = null;
let apiAvailableCheckedAt = 0;
const AVAILABILITY_RECHECK_MS = 60_000; // retry 60s after a failure

function logApiFallback(path: string, error: unknown) {
  if (warnedPaths.has(path)) return;
  warnedPaths.add(path);
  console.warn(`[api] Falling back for ${path}`, error);
}

async function apiListFetchWithLocaleFallback<T>(
  path: string,
  locale: string,
  fallback: ListResponse<T>,
  options?: RequestInit
): Promise<ListResponse<T>> {
  const localized = await apiFetch<ListResponse<T>>(path, fallback, options);
  if (!shouldFetchEnglishListFallback(locale, parseListPage(path))) {
    return localized;
  }

  const english = await apiFetch<ListResponse<T>>(
    withLocaleQuery(path, DEFAULT_CONTENT_LOCALE),
    fallback,
    options
  );
  const merged = mergePublishedListBySlug(localized.data ?? [], english.data ?? []);
  return {
    data: merged,
    meta: {
      total: Math.max(localized.meta?.total ?? 0, english.meta?.total ?? 0, merged.length),
      page: 1,
      page_size: Math.max(localized.meta?.page_size ?? 0, merged.length, 1),
      total_pages: Math.max(localized.meta?.total_pages ?? 0, english.meta?.total_pages ?? 0, merged.length > 0 ? 1 : 0),
    },
  };
}

async function isApiAvailable(): Promise<boolean> {
  const now = Date.now();
  // Return cached success (Next.js fetch revalidation handles staleness)
  if (apiAvailableResult === true) return true;
  // Return cached failure only within the retry window
  if (apiAvailableResult === false && now - apiAvailableCheckedAt < AVAILABILITY_RECHECK_MS) {
    return false;
  }
  // (Re-)check availability
  apiAvailableCheckedAt = now;
  try {
    const res = await fetch(`${BASE}/health`, {
      headers: { "Content-Type": "application/json" },
      next: { revalidate: 60 },
    });
    apiAvailableResult = res.ok;
  } catch (error) {
    if (!STRICT_BUILD_API) {
      logApiFallback("/health", error);
    }
    apiAvailableResult = false;
  }
  return apiAvailableResult;
}

// Server Components: no caching by default — use Next.js `fetch` cache options
async function apiFetch<T>(path: string, fallback: T, options?: RequestInit): Promise<T> {
  const url = `${BASE}/api/v1${path}`;
  const available = await isApiAvailable();
  if (!available) {
    if (STRICT_BUILD_API) {
      throw new Error(`Backend API unavailable during build for ${path}`);
    }
    console.error(`[api] Backend unavailable — returning empty fallback for ${path}`);
    return fallback;
  }

  try {
    const tenantRequest = await withRequestTenantHeaders({
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    });
    const res = await fetch(url, {
      ...options,
      headers: tenantRequest.headers,
      next: options?.next ?? {
        revalidate: 60,
        tags: [tenantCacheTag(tenantRequest.host)],
      },
    });
    if (!res.ok) {
      throw new Error(`API ${path} → ${res.status} ${res.statusText}`);
    }
    return res.json();
  } catch (error) {
    if (STRICT_BUILD_API) {
      throw error instanceof Error ? error : new Error(String(error));
    }
    console.error(`[api] Request failed for ${path}`, error);
    logApiFallback(path, error);
    return fallback;
  }
}

const emptyListResponse = <T>(data: T[] = []): ListResponse<T> => ({
  data,
  meta: {
    total: data.length,
    page: 1,
    page_size: data.length || 1,
    total_pages: data.length > 0 ? 1 : 0,
  },
});

// ── Public content API ────────────────────────────────────────────────────────

export async function getPublishedCategories(locale = "en"): Promise<ProductCategory[]> {
  const res = await apiListFetchWithLocaleFallback<ProductCategory>(
    `/content/categories?status=published&locale=${locale}&page_size=100`,
    locale,
    emptyListResponse<ProductCategory>()
  );
  return res.data;
}

export async function getCategoryBySlug(
  slug: string,
  locale = "en"
): Promise<ProductCategory | null> {
  const res = await apiListFetchWithLocaleFallback<ProductCategory>(
    `/content/categories?slug=${encodeURIComponent(slug)}&status=published&locale=${locale}&page_size=1`,
    locale,
    emptyListResponse<ProductCategory>()
  );
  return res.data[0] ?? null;
}

export async function getProductsByCategory(
  categoryId: string,
  locale = "en",
  page = 1,
  pageSize = 24,
  q?: string
): Promise<ListResponse<Product>> {
  const params = new URLSearchParams({
    category_id: categoryId,
    status: "published",
    locale,
    page: String(page),
    page_size: String(pageSize),
  });
  if (q) params.set("q", q);
  return apiListFetchWithLocaleFallback<Product>(
    `/content/products?${params.toString()}`,
    locale,
    emptyListResponse<Product>()
  );
}

export async function getProductBySlug(slug: string, locale = "en"): Promise<Product | null> {
  const res = await apiListFetchWithLocaleFallback<Product>(
    `/content/products?slug=${slug}&locale=${locale}&status=published&page_size=1`,
    locale,
    emptyListResponse<Product>()
  );
  return res.data[0] ?? null;
}

export async function getProductLocales(slug: string): Promise<Array<{ locale: string }>> {
  const res = await apiFetch<ListResponse<Product>>(
    `/content/products?slug=${slug}&page_size=20`,
    emptyListResponse<Product>()
  );
  return Array.from(
    new Set(res.data.map((item) => item.locale).filter(Boolean))
  ).map((locale) => ({ locale }));
}

export async function getPublishedProducts(
  locale = "en",
  page = 1,
  pageSize = 24
): Promise<ListResponse<Product>> {
  return apiListFetchWithLocaleFallback<Product>(
    `/content/products?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    locale,
    emptyListResponse<Product>()
  );
}

/** Fetch all published products for a locale. */
export async function getAllPublishedProducts(
  locale = "en",
  page = 1,
  pageSize = 100
): Promise<ListResponse<Product>> {
  return apiListFetchWithLocaleFallback<Product>(
    `/content/products?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    locale,
    emptyListResponse<Product>()
  );
}

/** Fetch featured (is_featured=true) published products. */
export async function getFeaturedProducts(locale = "en"): Promise<Product[]> {
  const res = await apiListFetchWithLocaleFallback<Product>(
    `/content/products?status=published&featured=true&locale=${locale}&page_size=8`,
    locale,
    emptyListResponse<Product>()
  );
  return res.data;
}

async function getPublishedPage(
  params: Record<string, string>,
  locale = DEFAULT_CONTENT_LOCALE
): Promise<Page | null> {
  const search = new URLSearchParams({
    status: "published",
    locale,
    page_size: "1",
    ...params,
  });

  const response = await apiFetch<ListResponse<Page>>(
    `/content/pages?${search.toString()}`,
    emptyListResponse<Page>()
  );
  const page = response.data[0] ?? null;
  if (page || locale === DEFAULT_CONTENT_LOCALE) {
    return page;
  }

  const fallbackSearch = new URLSearchParams({
    status: "published",
    locale: DEFAULT_CONTENT_LOCALE,
    page_size: "1",
    ...params,
  });
  const fallback = await apiFetch<ListResponse<Page>>(
    `/content/pages?${fallbackSearch.toString()}`,
    emptyListResponse<Page>()
  );
  return fallback.data[0] ?? null;
}

export async function getPublishedPageByType(pageType: string, locale = DEFAULT_CONTENT_LOCALE): Promise<Page | null> {
  return getPublishedPage({ page_type: pageType }, locale);
}

export async function getPublishedPageBySlug(slug: string, locale = DEFAULT_CONTENT_LOCALE): Promise<Page | null> {
  return getPublishedPage({ slug }, locale);
}

/** Fetch all published applications for a locale. */
export async function getAllPublishedApplications(
  locale = "en",
  page = 1,
  pageSize = 100
): Promise<ListResponse<Application>> {
  return apiListFetchWithLocaleFallback<Application>(
    `/content/applications?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    locale,
    emptyListResponse<Application>()
  );
}

export async function getPublishedApplications(
  locale = "en",
  page = 1,
  pageSize = 20
): Promise<ListResponse<Application>> {
  return apiListFetchWithLocaleFallback<Application>(
    `/content/applications?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    locale,
    emptyListResponse<Application>()
  );
}

export async function getApplicationBySlug(slug: string, locale = "en"): Promise<Application | null> {
  const res = await apiListFetchWithLocaleFallback<Application>(
    `/content/applications?slug=${slug}&locale=${locale}&page_size=1`,
    locale,
    emptyListResponse<Application>()
  );
  return res.data[0] ?? null;
}

export async function getApplicationLocales(slug: string): Promise<Array<{ locale: string }>> {
  const res = await apiFetch<ListResponse<Application>>(
    `/content/applications?slug=${slug}&page_size=20`,
    emptyListResponse<Application>()
  );
  return Array.from(
    new Set(res.data.map((item) => item.locale).filter(Boolean))
  ).map((locale) => ({ locale }));
}

export async function getPublishedCertifications(locale = "en"): Promise<Certification[]> {
  const res = await apiListFetchWithLocaleFallback<Certification>(
    `/content/certifications?status=published&locale=${locale}&page_size=50`,
    locale,
    emptyListResponse<Certification>()
  );
  return res.data;
}

export async function getCertificationBySlug(slug: string, locale = "en"): Promise<Certification | null> {
  const res = await apiListFetchWithLocaleFallback<Certification>(
    `/content/certifications?status=published&locale=${locale}&slug=${encodeURIComponent(slug)}&page_size=1`,
    locale,
    emptyListResponse<Certification>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedCapabilities(locale = "en"): Promise<Capability[]> {
  const res = await apiListFetchWithLocaleFallback<Capability>(
    `/content/capabilities?status=published&locale=${locale}&page_size=30`,
    locale,
    emptyListResponse<Capability>()
  );
  return res.data;
}

export async function getCapabilityBySlug(slug: string, locale = "en"): Promise<Capability | null> {
  const res = await apiListFetchWithLocaleFallback<Capability>(
    `/content/capabilities?status=published&locale=${locale}&slug=${encodeURIComponent(slug)}&page_size=1`,
    locale,
    emptyListResponse<Capability>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedFAQs(
  locale = "en",
  categoryTag?: string
): Promise<FAQItem[]> {
  const tag = categoryTag ? `&category_tag=${categoryTag}` : "";
  const res = await apiListFetchWithLocaleFallback<FAQItem>(
    `/content/faqs?status=published&locale=${locale}&page_size=50${tag}`,
    locale,
    emptyListResponse<FAQItem>()
  );
  return res.data;
}

export async function getCTAByKey(key: string, locale = "en"): Promise<CTA | null> {
  const res = await apiListFetchWithLocaleFallback<CTA>(
    `/content/ctas?cta_key=${key}&locale=${locale}&page_size=1`,
    locale,
    emptyListResponse<CTA>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedComparisons(locale = "en"): Promise<ComparisonTopic[]> {
  const res = await apiListFetchWithLocaleFallback<ComparisonTopic>(
    `/content/comparisons?status=published&locale=${locale}&page_size=50`,
    locale,
    emptyListResponse<ComparisonTopic>()
  );
  return res.data;
}

export async function getComparisonBySlug(
  slug: string,
  locale = "en"
): Promise<ComparisonTopic | null> {
  const res = await apiListFetchWithLocaleFallback<ComparisonTopic>(
    `/content/comparisons?slug=${encodeURIComponent(slug)}&status=published&locale=${locale}&page_size=1`,
    locale,
    emptyListResponse<ComparisonTopic>()
  );
  return res.data[0] ?? null;
}

// ── Public M2M Relation APIs (1a.5.12) ────────────────────────────────────────

export interface PublicRelatedApplication {
  id: string;
  application_name: string;
  slug: string;
  industry?: string;
  description?: string;
}

export interface PublicRelatedProduct {
  id: string;
  product_name: string;
  slug: string;
  category_slug?: string;
  model_number?: string;
  short_description?: string;
}

export interface PublicRelatedCertification {
  id: string;
  cert_name: string;
  issuing_body?: string;
  description?: string;
  badge_icon_url?: string;
}

export interface PublicRelatedFAQ {
  id: string;
  question: string;
  answer: string;
  locale?: string;
}

export async function getProductRelatedApplications(
  productId: string
): Promise<PublicRelatedApplication[]> {
  return apiFetch<PublicRelatedApplication[]>(
    `/content/public/products/${productId}/applications`,
    []
  );
}

export async function getApplicationRelatedProducts(
  applicationId: string
): Promise<PublicRelatedProduct[]> {
  return apiFetch<PublicRelatedProduct[]>(
    `/content/public/applications/${applicationId}/products`,
    []
  );
}

export async function getProductRelatedCertifications(
  productId: string
): Promise<PublicRelatedCertification[]> {
  return apiFetch<PublicRelatedCertification[]>(
    `/content/public/products/${productId}/certifications`,
    []
  );
}

export async function getProductRelatedFAQs(
  productId: string
): Promise<PublicRelatedFAQ[]> {
  return apiFetch<PublicRelatedFAQ[]>(
    `/content/public/products/${productId}/faqs`,
    []
  );
}
export async function getProductAlternatives(
  productId: string
): Promise<PublicRelatedProduct[]> {
  return apiFetch<PublicRelatedProduct[]>(
    `/content/public/products/${productId}/alternatives`,
    []
  );
}

export async function getApplicationRelatedFAQs(
  applicationId: string
): Promise<PublicRelatedFAQ[]> {
  return apiFetch<PublicRelatedFAQ[]>(
    `/content/public/applications/${applicationId}/faqs`,
    []
  );
}
