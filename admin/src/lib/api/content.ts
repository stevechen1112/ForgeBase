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
  og_image_url: string | null;
  image_alt: string | null;
  status: string;
  locale: string;
  is_featured: boolean;
  display_priority: number;
  created_at: string;
  updated_at: string;
  published_at: string | null;
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
  target_intent_stage: string;
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
  brief_id: string | null;
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

export type PageBrief = {
  id: string;
  target_page_type: string;
  target_slug: string | null;
  title_draft: string | null;
  audience_persona: string | null;
  buyer_stage: string | null;
  primary_keyword: string | null;
  secondary_keywords: string | null;
  tone: string | null;
  word_count_target: number | null;
  main_cta_key: string | null;
  notes: string | null;
  ai_status: string;
  locale: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type SEOEvaluationCheck = {
  id: string;
  label: string;
  status: "good" | "warning" | "critical";
  message: string;
};

export type SEOEvaluationSuggestion = {
  id: string;
  title: string;
  detail: string;
  priority: "high" | "medium" | "low";
  field?: string;
  suggested_value?: string | null;
};

export type SEOEvaluation = {
  entity_type: string;
  entity_label: string;
  entity_name: string;
  score: number;
  status: "healthy" | "needs-work" | "critical";
  summary: string;
  focus_keywords: string[];
  search_preview: {
    title: string;
    description: string;
    url: string;
  };
  checks: SEOEvaluationCheck[];
  suggestions: SEOEvaluationSuggestion[];
  recommended: {
    seo_title: string;
    seo_description: string;
    canonical_url: string;
  };
};

export type SEOHealthTask = {
  id: string;
  title: string;
  description: string;
  count: number;
  impact: string;
  entity_types: string[];
};

export type SEOHealthEntity = {
  id: string;
  entity_type: string;
  name: string;
  score: number;
  status: "healthy" | "needs-work" | "critical";
  url: string;
  focus_keywords: string[];
  top_issue: string;
};

export type SEOHealthResponse = {
  summary: {
    total_entities: number;
    healthy: number;
    needs_work: number;
    critical: number;
    avg_score: number;
    published_pages: number;
    published_products: number;
    published_categories: number;
    published_applications: number;
  };
  tasks: SEOHealthTask[];
  entities: SEOHealthEntity[];
};

export type SEOLinkOpportunity = {
  source_type: string;
  source_name: string;
  source_url: string;
  target_type: string;
  target_name: string;
  target_url: string;
  reason: string;
  confidence: string;
};

export type SEOLinksResponse = {
  count: number;
  suggestions: SEOLinkOpportunity[];
};

export type SEORevenueRow = {
  page_id: string;
  page_type: string;
  page_name: string;
  page_views: number;
  unique_visitors: number;
  rfq_count: number;
  avg_intent_score: number;
  conversion_rate: number;
};

export type SEORevenueResponse = {
  summary: {
    total_views: number;
    total_rfq: number;
    pages_with_rfq: number;
    avg_conversion_rate: number;
  };
  top_converters: SEORevenueRow[];
  underperformers: SEORevenueRow[];
};

export type SEOAuditSummaryResponse = {
  on_page: {
    total_published_pages: number;
    ok: number;
    warning: number;
    critical: number;
    no_meta_description: number;
    no_structured_data: number;
    has_canonical: number;
    structured_data_coverage_pct: number;
  };
  gsc: {
    total_clicks: number;
    total_impressions: number;
    avg_ctr_pct: number;
    avg_position: number | null;
    opportunity_pages: number;
    days: number;
    data_available: boolean;
  };
};

export type SEOAuditPageIssue = {
  id: string;
  slug: string;
  title: string;
  page_type: string;
  locale: string;
  status: string;
  seo_title: string | null;
  seo_title_length: number;
  seo_description: string | null;
  seo_description_length: number;
  has_structured_data: boolean;
  has_canonical: boolean;
  noindex: boolean;
  body_length: number;
  issues: string[];
  severity: "ok" | "warning" | "critical";
};

export type SEOOpportunitiesResponse = {
  days: number;
  count: number;
  pages: Array<{
    page: string;
    clicks: number;
    impressions: number;
    ctr: number;
    avg_position: number;
  }>;
};

export type SEOCannibalizationResponse = {
  days: number;
  count: number;
  queries: Array<{
    query: string;
    pages: Array<{
      page: string;
      clicks: number;
      position: number;
    }>;
  }>;
};

export type SEOOnPageResponse = {
  total: number;
  pages: SEOAuditPageIssue[];
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
export const briefsApi = makeContentApi<PageBrief, Partial<PageBrief>, Partial<PageBrief>>(`${BASE}/briefs`);

export const seoWorkbenchApi = {
  evaluate: (token: string, payload: { entity_type: string; data: Record<string, unknown> }) =>
    apiClient.post<SEOEvaluation>(`${BASE}/seo-audit/evaluate`, payload, token),
  health: (token: string) =>
    apiClient.get<SEOHealthResponse>(`${BASE}/seo-audit/health`, token),
  links: (token: string, limit = 20) =>
    apiClient.get<SEOLinksResponse>(`${BASE}/seo-audit/links?limit=${limit}`, token),
  revenue: (token: string, days = 30) =>
    apiClient.get<SEORevenueResponse>(`${BASE}/seo-audit/revenue?days=${days}`, token),
  summary: (token: string, days = 28) =>
    apiClient.get<SEOAuditSummaryResponse>(`${BASE}/seo-audit/summary?days=${days}`, token),
  onPage: (token: string, params?: { severity?: string; page_type?: string; locale?: string }) => {
    const qs = params ? "?" + new URLSearchParams(params as Record<string, string>).toString() : "";
    return apiClient.get<SEOOnPageResponse>(`${BASE}/seo-audit/on-page${qs}`, token);
  },
  opportunities: (token: string, days = 28) =>
    apiClient.get<SEOOpportunitiesResponse>(`${BASE}/seo-audit/opportunities?days=${days}`, token),
  cannibalization: (token: string, days = 28) =>
    apiClient.get<SEOCannibalizationResponse>(`${BASE}/seo-audit/cannibalization?days=${days}`, token),
};

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
    apiClient.del<void>(`${BASE}/applications/${applicationId}/faqs/${faqId}`, token),};
// ── Content Strategy ──────────────────────────────────────────────────────────
export type ContentStrategy = {
  id: string;
  page_type: string;
  entity_type: string | null;
  entity_id: string | null;
  brief_id: string | null;
  status: "unplanned" | "brief_created" | "ai_generated" | "in_review" | "published";
  locale: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export const strategiesApi = makeContentApi<
  ContentStrategy,
  Partial<ContentStrategy>,
  Partial<ContentStrategy>
>(`${BASE}/strategies`);

// ── Content Asset ─────────────────────────────────────────────────────────────
export type ContentAsset = {
  id: string;
  original_filename: string;
  r2_key: string;
  public_url: string;
  mime_type: string;
  file_size_bytes: number;
  asset_type: "image" | "pdf" | "cad" | "other";
  alt_text: string | null;
  title: string | null;
  is_indexable: boolean;
  seo_title: string | null;
  requires_gate: boolean;
  entity_type: string | null;
  entity_id: string | null;
  locale: string;
  uploaded_by: string;
  created_at: string;
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
  updateAlt: (token: string, id: string, altText: string) =>
    apiClient.patch<ContentAsset>(`${BASE}/assets/${id}`, { alt_text: altText }, token),
  toggleGate: (token: string, id: string, requiresGate: boolean) =>
    apiClient.patch<ContentAsset>(`${BASE}/assets/${id}`, { requires_gate: requiresGate }, token),
};