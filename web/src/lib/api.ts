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
} from "@/types/content";

const BASE = process.env.API_INTERNAL_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const warnedPaths = new Set<string>();
let apiAvailabilityPromise: Promise<boolean> | null = null;

function logApiFallback(path: string, error: unknown) {
  if (warnedPaths.has(path)) return;
  warnedPaths.add(path);
  console.warn(`[api] Falling back for ${path}`, error);
}

async function isApiAvailable(): Promise<boolean> {
  if (!apiAvailabilityPromise) {
    apiAvailabilityPromise = fetch(`${BASE}/health`, {
      headers: { "Content-Type": "application/json" },
      next: { revalidate: 60 },
    })
      .then((res) => res.ok)
      .catch((error) => {
        logApiFallback("/health", error);
        return false;
      });
  }

  return apiAvailabilityPromise;
}

// Server Components: no caching by default — use Next.js `fetch` cache options
async function apiFetch<T>(path: string, fallback: T, options?: RequestInit): Promise<T> {
  const url = `${BASE}/api/v1${path}`;
  const available = await isApiAvailable();
  if (!available) {
    return fallback;
  }

  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      next: { revalidate: 60 },  // ISR: revalidate every 60s
      ...options,
    });
    if (!res.ok) {
      throw new Error(`API ${path} → ${res.status} ${res.statusText}`);
    }
    return res.json();
  } catch (error) {
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
  const res = await apiFetch<ListResponse<ProductCategory>>(
    `/content/categories?status=published&locale=${locale}&page_size=100`,
    emptyListResponse<ProductCategory>()
  );
  return res.data;
}

export async function getCategoryBySlug(slug: string): Promise<ProductCategory | null> {
  const res = await apiFetch<ListResponse<ProductCategory>>(
    `/content/categories?slug=${slug}&page_size=1`,
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
  return apiFetch<ListResponse<Product>>(`/content/products?${params.toString()}`, emptyListResponse<Product>());
}

export async function getProductBySlug(slug: string, locale = "en"): Promise<Product | null> {
  const res = await apiFetch<ListResponse<Product>>(
    `/content/products?slug=${slug}&locale=${locale}&page_size=1`,
    emptyListResponse<Product>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedProducts(
  locale = "en",
  page = 1,
  pageSize = 24
): Promise<ListResponse<Product>> {
  return apiFetch<ListResponse<Product>>(
    `/content/products?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    emptyListResponse<Product>()
  );
}

/** Fetch all published products for a locale. */
export async function getAllPublishedProducts(
  locale = "en",
  page = 1,
  pageSize = 100
): Promise<ListResponse<Product>> {
  return apiFetch<ListResponse<Product>>(
    `/content/products?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    emptyListResponse<Product>()
  );
}

/** Fetch featured (is_featured=true) published products. */
export async function getFeaturedProducts(locale = "en"): Promise<Product[]> {
  const res = await apiFetch<ListResponse<Product>>(
    `/content/products?status=published&featured=true&locale=${locale}&page_size=8`,
    emptyListResponse<Product>()
  );
  return res.data;
}

/** Fetch all published applications for a locale. */
export async function getAllPublishedApplications(
  locale = "en",
  page = 1,
  pageSize = 100
): Promise<ListResponse<Application>> {
  return apiFetch<ListResponse<Application>>(
    `/content/applications?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    emptyListResponse<Application>()
  );
}

export async function getPublishedApplications(
  locale = "en",
  page = 1,
  pageSize = 20
): Promise<ListResponse<Application>> {
  return apiFetch<ListResponse<Application>>(
    `/content/applications?status=published&locale=${locale}&page=${page}&page_size=${pageSize}`,
    emptyListResponse<Application>()
  );
}

export async function getApplicationBySlug(slug: string, locale = "en"): Promise<Application | null> {
  const res = await apiFetch<ListResponse<Application>>(
    `/content/applications?slug=${slug}&locale=${locale}&page_size=1`,
    emptyListResponse<Application>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedCertifications(locale = "en"): Promise<Certification[]> {
  const res = await apiFetch<ListResponse<Certification>>(
    `/content/certifications?status=published&locale=${locale}&page_size=50`,
    emptyListResponse<Certification>()
  );
  return res.data;
}

export async function getCertificationBySlug(slug: string, locale = "en"): Promise<Certification | null> {
  const res = await apiFetch<ListResponse<Certification>>(
    `/content/certifications?status=published&locale=${locale}&slug=${encodeURIComponent(slug)}&page_size=1`,
    emptyListResponse<Certification>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedCapabilities(locale = "en"): Promise<Capability[]> {
  const res = await apiFetch<ListResponse<Capability>>(
    `/content/capabilities?status=published&locale=${locale}&page_size=30`,
    emptyListResponse<Capability>()
  );
  return res.data;
}

export async function getCapabilityBySlug(slug: string, locale = "en"): Promise<Capability | null> {
  const res = await apiFetch<ListResponse<Capability>>(
    `/content/capabilities?status=published&locale=${locale}&slug=${encodeURIComponent(slug)}&page_size=1`,
    emptyListResponse<Capability>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedFAQs(
  locale = "en",
  categoryTag?: string
): Promise<FAQItem[]> {
  const tag = categoryTag ? `&category_tag=${categoryTag}` : "";
  const res = await apiFetch<ListResponse<FAQItem>>(
    `/content/faqs?status=published&locale=${locale}&page_size=50${tag}`,
    emptyListResponse<FAQItem>()
  );
  return res.data;
}

export async function getCTAByKey(key: string, locale = "en"): Promise<CTA | null> {
  const res = await apiFetch<ListResponse<CTA>>(
    `/content/ctas?cta_key=${key}&locale=${locale}&page_size=1`,
    emptyListResponse<CTA>()
  );
  return res.data[0] ?? null;
}

export async function getPublishedComparisons(locale = "en"): Promise<ComparisonTopic[]> {
  const res = await apiFetch<ListResponse<ComparisonTopic>>(
    `/content/comparisons?status=published&locale=${locale}&page_size=50`,
    emptyListResponse<ComparisonTopic>()
  );
  return res.data;
}

export async function getComparisonBySlug(slug: string): Promise<ComparisonTopic | null> {
  const res = await apiFetch<ListResponse<ComparisonTopic>>(
    `/content/comparisons?slug=${encodeURIComponent(slug)}&status=published&page_size=1`,
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

export interface LocaleVariant {
  id: string;
  locale: string;
  product_name?: string;
  application_name?: string;
}

export async function getProductLocales(slug: string): Promise<LocaleVariant[]> {
  return apiFetch<LocaleVariant[]>(`/content/public/products/${slug}/locales`, []);
}

export async function getApplicationLocales(slug: string): Promise<LocaleVariant[]> {
  return apiFetch<LocaleVariant[]>(`/content/public/applications/${slug}/locales`, []);
}

export async function getProductAlternatives(
  productId: string
): Promise<PublicRelatedProduct[]> {
  return apiFetch<PublicRelatedProduct[]>(
    `/content/public/products/${productId}/alternatives`,
    []
  );
}

export interface IndexedDoc {
  id: string;
  title: string | null;
  seo_title: string | null;
  public_url: string;
  mime_type: string;
  file_size_bytes: number;
  requires_gate: boolean;
  product_id: string | null;
  created_at: string;
}

export async function getIndexedDocuments(): Promise<IndexedDoc[]> {
  return apiFetch<IndexedDoc[]>("/content/assets/public/indexed-docs", []);
}

export async function getProductIndexedDocs(productId: string): Promise<IndexedDoc[]> {
  return apiFetch<IndexedDoc[]>(`/content/assets/public/indexed-docs?product_id=${productId}`, []);
}

export async function getApplicationRelatedFAQs(
  applicationId: string
): Promise<PublicRelatedFAQ[]> {
  return apiFetch<PublicRelatedFAQ[]>(
    `/content/public/applications/${applicationId}/faqs`,
    []
  );
}
