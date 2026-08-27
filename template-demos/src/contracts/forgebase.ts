export type TemplateStatus = "ready" | "planned" | "retired";

export type CTAIntent =
  | "view_product"
  | "request_quote"
  | "contact_sales"
  | "download_spec"
  | "request_sample"
  | "book_meeting"
  | "ask_question";

export interface DemoDisclosure {
  label: string;
  message: string;
}

export interface TemplateSiteProfile {
  companyName: string;
  legalNotice: string;
  tagline: string;
  description: string;
  email: string;
  phone?: string;
  location: string;
  disclosure: DemoDisclosure;
}

export interface TemplateCTA {
  id: string;
  label: string;
  href: string;
  intent: CTAIntent;
  variant?: "primary" | "secondary" | "text";
}

export interface TemplateAttribute {
  label: string;
  value: string;
}

export interface TemplateCategory {
  id: string;
  slug: string;
  name: string;
  description?: string;
}

export interface TemplateProduct {
  id: string;
  slug: string;
  name: string;
  modelNumber?: string;
  shortDescription: string;
  categoryId?: string;
  attributes: TemplateAttribute[];
  applications?: string[];
  cta: TemplateCTA;
}

export interface TemplateApplication {
  id: string;
  slug: string;
  name: string;
  description: string;
}

export interface TemplateCapability {
  id: string;
  slug: string;
  name: string;
  description: string;
  metrics?: TemplateAttribute[];
}

export interface TemplateCertification {
  id: string;
  name: string;
  scope: string;
  demoOnly: true;
}

export interface TemplateFAQItem {
  id: string;
  question: string;
  answer: string;
}

export interface TemplateRFQField {
  id: string;
  label: string;
  type: "text" | "email" | "tel" | "select" | "textarea" | "file";
  required?: boolean;
  placeholder?: string;
  options?: string[];
  forgeBaseField?: string;
}

export interface TemplateManifest {
  slug: string;
  name: string;
  industry: string;
  summary: string;
  buyerRoles: string[];
  status: TemplateStatus;
  visualDirection: string;
  accent: string;
  routes: string[];
  forgeBaseEntities: string[];
  customDataNotes?: string[];
}

export interface TemplateDemoData {
  site: TemplateSiteProfile;
  ctas: TemplateCTA[];
  categories: TemplateCategory[];
  products: TemplateProduct[];
  applications: TemplateApplication[];
  capabilities: TemplateCapability[];
  certifications: TemplateCertification[];
  faqs: TemplateFAQItem[];
  rfqFields: TemplateRFQField[];
}
