import type { TemplateManifest } from "@/contracts/forgebase";

export const electronicComponentsManifest: TemplateManifest = {
  slug: "electronic-components",
  name: "Electronic Components",
  industry: "Components and technical distribution",
  summary: "A specification-dense catalogue for part-number discovery, parametric comparison and sample requests.",
  buyerRoles: ["Hardware engineer", "Component engineer", "Strategic buyer"],
  status: "ready",
  visualDirection: "High-density engineering catalogue with dominant part search, family index, parametric tables, datasheet records and a sample cart.",
  accent: "#60a5fa",
  routes: ["/", "/products", "/products/[slug]", "/categories/[slug]", "/applications", "/certifications", "/resources", "/about", "/rfq"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Parametric filters derive from normalized Product.attributes.",
    "Datasheet versioning and sample fulfillment require future document and workflow adapters.",
  ],
};
