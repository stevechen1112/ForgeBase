/**
 * Typed API functions for all content CRUD endpoints.
 * All return { data, meta } from APIResponse.
 */
import { apiClient } from "./client";

export type PaginationMeta = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type APIListResponse<T> = {
  data: T[];
  meta: PaginationMeta;
};

export type APIItemResponse<T> = {
  data: T;
  meta?: null;
};

// ── Generic list/get/create/update/delete ─────────────────────────────────────
function makeContentApi<T, CreatePayload, UpdatePayload>(base: string) {
  return {
    list: (token: string, params?: Record<string, string | number>) => {
      const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
      return apiClient.get<APIListResponse<T>>(`${base}${qs}`, token);
    },
    get: (token: string, id: string) =>
      apiClient.get<APIItemResponse<T>>(`${base}/${id}`, token),
    create: (token: string, payload: CreatePayload) =>
      apiClient.post<APIItemResponse<T>>(base, payload, token),
    update: (token: string, id: string, payload: UpdatePayload) =>
      apiClient.patch<APIItemResponse<T>>(`${base}/${id}`, payload, token),
    delete: (token: string, id: string) =>
      apiClient.del<void>(`${base}/${id}`, token),
  };
}

// ── Type definitions mirroring Python schemas ─────────────────────────────────

export type ProductCategory = {
  id: string;
  category_name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  og_image_url: string | null;
  parent_id: string | null;
  sort_order: number;
  seo_title: string | null;
  seo_description: string | null;
  status: string;
  locale: string;
  created_at: string;
  updated_at: string;
};

export type Product = {
  id: string;
  product_name: string;
  slug: string;
  model_number: string;
  short_description: string;
  full_description: string | null;
  specifications: string | null;
  category_id: string;
  seo_title: string | null;
  seo_description: string | null;
  image_url: string | null;
  og_image_url: string | null;
  image_alt: string | null;
  status: string;
  locale: string;
  is_featured: boolean;
  display_priority: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
  gallery_images?: ProductGalleryImage[];
};

export type Application = {
  id: string;
  application_name: string;
  slug: string;
  industry: string;
  description: string | null;
  challenge: string | null;
  solution: string | null;
  hero_image_url: string | null;
  og_image_url: string | null;
  seo_title: string | null;
  seo_description: string | null;
  status: string;
  locale: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
};

export type FAQItem = {
  id: string;
  variant_key?: string;
  question: string;
  answer: string;
  category_tag: string | null;
  locale: string;
  sort_order: number;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ComparisonTopic = {
  id: string;
  topic_title: string;
  slug: string;
  summary: string | null;
  dimensions: string | null;
  conclusion: string | null;
  seo_title: string | null;
  seo_description: string | null;
  status: string;
  locale: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
};

export type Certification = {
  id: string;
  cert_name: string;
  slug: string;
  issuer: string | null;
  cert_number: string | null;
  issued_at: string | null;
  expires_at: string | null;
  description: string | null;
  badge_image_url: string | null;
  document_url: string | null;
  locale: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CTA = {
  id: string;
  cta_key: string;
  cta_type: string;
  headline: string;
  subheadline: string | null;
  button_label: string;
  button_action: string;
  button_url: string | null;
  bg_color: string | null;
  image_url: string | null;
  locale: string;
  status: string;
  sort_order: number;
  created_at: string;
  updated_at: string;
};

export type Page = {
  id: string;
  page_type: string;
  slug: string;
  title: string;
  subtitle: string | null;
  body: string | null;
  hero_image_url: string | null;
  seo_title: string | null;
  seo_description: string | null;
  og_image_url: string | null;
  canonical_url: string | null;
  structured_data: string | null;
  locale: string;
  status: string;
  noindex: boolean;
  entity_type: string | null;
  entity_id: string | null;
  created_at: string;
  updated_at: string;
  published_at: string | null;
};

export type RedirectRule = {
  id: string;
  from_path: string;
  to_path: string;
  status_code: 301 | 302;
  is_active: boolean;
  note: string;
  created_at: string;
  updated_at: string;
};

// ── API client instances ──────────────────────────────────────────────────────
const BASE = "/content";

export const categoriesApi = makeContentApi<ProductCategory, Partial<ProductCategory>, Partial<ProductCategory>>(`${BASE}/categories`);
export const productsApi = makeContentApi<Product, Partial<Product>, Partial<Product>>(`${BASE}/products`);
export const applicationsApi = makeContentApi<Application, Partial<Application>, Partial<Application>>(`${BASE}/applications`);
export const faqsApi = makeContentApi<FAQItem, Partial<FAQItem>, Partial<FAQItem>>(`${BASE}/faqs`);
export const comparisonsApi = makeContentApi<ComparisonTopic, Partial<ComparisonTopic>, Partial<ComparisonTopic>>(`${BASE}/comparisons`);
export const certificationsApi = makeContentApi<Certification, Partial<Certification>, Partial<Certification>>(`${BASE}/certifications`);

export type Capability = {
  id: string;
  capability_name: string;
  slug: string;
  icon_url: string | null;
  image_url: string | null;
  short_description: string;
  detail: string | null;
  metrics: string | null;
  category_tag: string | null;
  sort_order: number;
  locale: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export const capabilitiesApi = makeContentApi<Capability, Partial<Capability>, Partial<Capability>>(`${BASE}/capabilities`);

export const ctasApi = makeContentApi<CTA, Partial<CTA>, Partial<CTA>>(`${BASE}/ctas`);
export const pagesApi = makeContentApi<Page, Partial<Page>, Partial<Page>>(`${BASE}/pages`);
export const redirectsApi = {
  list: (token: string, activeOnly = false) =>
    apiClient.get<RedirectRule[]>(`${BASE}/redirects?active_only=${String(activeOnly)}`, token),
  create: (token: string, payload: Partial<RedirectRule>) =>
    apiClient.post<RedirectRule>(`${BASE}/redirects`, payload, token),
  update: (token: string, id: string, payload: Partial<RedirectRule>) =>
    apiClient.patch<RedirectRule>(`${BASE}/redirects/${id}`, payload, token),
  delete: (token: string, id: string) =>
    apiClient.del<void>(`${BASE}/redirects/${id}`, token),
};
// ── Preview Token (1a.6.4) ────────────────────────────────────────────────────
export const previewApi = {
  createToken: (token: string, pageId: string) =>
    apiClient.post<{ token: string; expires_in_seconds: number; preview_url: string }>(
      `${BASE}/pages/${pageId}/preview-token`,
      {},
      token
    ),
};

// ── Publish / Unpublish ───────────────────────────────────────────────────────
export const localeDraftApi = {
  create: (token: string, entity: string, id: string, targetLocale?: string) =>
    apiClient.post<{
      action: string;
      entity: string;
      source_id: string;
      target_id: string;
      source_locale: string;
      target_locale: string;
      status: string;
    }>(`${BASE}/${entity}/${id}/locale-draft`, { target_locale: targetLocale ?? null }, token),
  createBatch: (token: string, entity: string, sourceIds: string[], targetLocale: string) =>
    apiClient.post<{
      entity: string;
      target_locale: string;
      requested: number;
      created_or_updated: number;
      failed: number;
      failures: Array<{ source_id: string; status_code: number; message: string }>;
      published: number;
    }>(`${BASE}/locale-drafts/batch`, {
      entity,
      source_ids: sourceIds,
      target_locale: targetLocale,
    }, token),
};

export const localeCoverageApi = {
  get: (token: string, targetLocale?: string) =>
    apiClient.get<{
      source_locale: string;
      target_locale: string;
      source_total: number;
      translated: number;
      overall_coverage_pct: number | null;
      missing: number;
      draft: number;
      stale: number;
      unpaired: number;
      entities: Array<{ entity: string; missing_keys: string[]; missing_ids: string[]; missing_count: number; draft: number; stale: number; unpaired: number; unpaired_keys: string[]; source_total: number; translated: number; published: number; coverage_pct: number | null; published_pct: number | null }>;
      policy: string;
    }>(`${BASE}/locale-coverage${targetLocale ? `?target_locale=${encodeURIComponent(targetLocale)}` : ""}`, token),
  settings: (token: string) =>
    apiClient.get<{
      source_locale: string;
      content_locales: Array<{ content_locale: string; route_locale: string; label: string; native_label: string; public_shell_ready: boolean }>;
      public_shell_locales: string[];
      policy: string;
    }>(`${BASE}/locale-settings`, token),
};

export const publishApi = {
  publish: (token: string, entity: string, id: string) =>
    apiClient.post<{ detail: string; id: string }>(`${BASE}/${entity}/${id}/publish`, {}, token),
  unpublish: (token: string, entity: string, id: string) =>
    apiClient.post<{ detail: string; id: string }>(`${BASE}/${entity}/${id}/unpublish`, {}, token),
};

// ── M2M Relations ─────────────────────────────────────────────────────────────
export const relationsApi = {
  listProductApplications: (token: string, productId: string) =>
    apiClient.get<{ id: string; name: string; slug: string }[]>(`${BASE}/products/${productId}/applications`, token),
  linkProductApplication: (token: string, productId: string, appId: string) =>
    apiClient.post<{ detail: string }>(`${BASE}/products/${productId}/applications/${appId}`, {}, token),
  unlinkProductApplication: (token: string, productId: string, appId: string) =>
    apiClient.del<void>(`${BASE}/products/${productId}/applications/${appId}`, token),

  listProductCertifications: (token: string, productId: string) =>
    apiClient.get<{ id: string; name: string; slug: string }[]>(`${BASE}/products/${productId}/certifications`, token),
  linkProductCertification: (token: string, productId: string, certId: string) =>
    apiClient.post<{ detail: string }>(`${BASE}/products/${productId}/certifications/${certId}`, {}, token),
  unlinkProductCertification: (token: string, productId: string, certId: string) =>
    apiClient.del<void>(`${BASE}/products/${productId}/certifications/${certId}`, token),

  listProductFAQs: (token: string, productId: string) =>
    apiClient.get<{ id: string; name: string; slug: string }[]>(`${BASE}/products/${productId}/faqs`, token),
  linkProductFAQ: (token: string, productId: string, faqId: string) =>
    apiClient.post<{ detail: string }>(`${BASE}/products/${productId}/faqs/${faqId}`, {}, token),
  unlinkProductFAQ: (token: string, productId: string, faqId: string) =>
    apiClient.del<void>(`${BASE}/products/${productId}/faqs/${faqId}`, token),
  listApplicationFAQs: (token: string, applicationId: string) =>
    apiClient.get<{ id: string; name: string; slug: string }[]>(`${BASE}/applications/${applicationId}/faqs`, token),
  linkApplicationFAQ: (token: string, applicationId: string, faqId: string) =>
    apiClient.post<{ detail: string }>(`${BASE}/applications/${applicationId}/faqs/${faqId}`, {}, token),
  unlinkApplicationFAQ: (token: string, applicationId: string, faqId: string) =>
    apiClient.del<void>(`${BASE}/applications/${applicationId}/faqs/${faqId}`, token),
};

// ── Content Asset ─────────────────────────────────────────────────────────────
export type ContentAsset = {
  id: string;
  original_filename: string;
  r2_key: string;
  public_url: string;
  mime_type: string;
  file_size_bytes: number;
  asset_type: "image" | "pdf" | "cad" | "document" | "other";
  alt_text: string | null;
  title: string | null;
  is_indexable: boolean;
  index_status?: "not_indexed" | "not_applicable" | "pending" | "indexed" | "needs_ocr" | "withdrawn";
  index_error?: string | null;
  seo_title: string | null;
  product_id: string | null;
  page_id: string | null;
  display_order: number;
  uploaded_by: string;
  created_at: string;
};

export type ProductGalleryImage = {
  id: string;
  public_url: string;
  alt_text: string | null;
  display_order: number;
};

export const assetsApi = {
  list: (token: string, params?: Record<string, string | number>) => {
    const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
    return apiClient.get<APIListResponse<ContentAsset>>(`${BASE}/assets${qs}`, token);
  },
  upload: (token: string, formData: FormData) =>
    apiClient.postForm<ContentAsset>(`${BASE}/assets`, formData, token),
  delete: (token: string, id: string) =>
    apiClient.del<void>(`${BASE}/assets/${id}`, token),
  update: (token: string, id: string, payload: Partial<Pick<ContentAsset, "alt_text" | "display_order" | "product_id" | "is_indexable" | "title">>) =>
    apiClient.patch<ContentAsset>(`${BASE}/assets/${id}`, payload, token),
  updateAlt: (token: string, id: string, altText: string) =>
    apiClient.patch<ContentAsset>(`${BASE}/assets/${id}`, { alt_text: altText }, token),
};

export const productGalleryApi = {
  reorder: (token: string, productId: string, items: Array<{ id: string; display_order: number }>) =>
    apiClient.put<APIItemResponse<Product>>(`${BASE}/products/${productId}/gallery`, { items }, token),
};
