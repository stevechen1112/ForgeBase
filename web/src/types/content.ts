// Shared TypeScript types mirroring backend content models.
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
};

export type Product = {
  id: string;
  product_name: string;
  slug: string;
  model_number: string;
  short_description: string;
  full_description: string | null;
  specifications: string | null;   // JSON string
  category_id: string;
  image_url?: string | null;
  seo_title: string | null;
  seo_description: string | null;
  og_image_url: string | null;
  image_alt: string | null;
  status: string;
  locale: string;
  is_featured: boolean;
  display_priority: number;
  published_at: string | null;
  gallery_images?: Array<{
    id: string;
    public_url: string;
    alt_text: string | null;
    display_order: number;
  }>;
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
};

export type FAQItem = {
  id: string;
  question: string;
  answer: string;
  category_tag: string | null;
  locale: string;
  sort_order: number;
  status: string;
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
  locale: string;
  status: string;
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
  created_at?: string;
  updated_at?: string;
  published_at?: string | null;
};

export type Capability = {
  id: string;
  capability_name: string;
  slug: string;
  icon_url: string | null;
  short_description: string;
  detail: string | null;
  category_tag: string | null;
  sort_order: number;
  locale: string;
  status: string;
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
};

export type PaginationMeta = {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type ListResponse<T> = { data: T[]; meta: PaginationMeta };
export type ItemResponse<T> = { data: T };
