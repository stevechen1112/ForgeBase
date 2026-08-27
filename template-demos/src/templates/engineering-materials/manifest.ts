import type { TemplateManifest } from "@/contracts/forgebase";

export const engineeringMaterialsManifest: TemplateManifest = {
  slug: "engineering-materials",
  name: "Engineering Materials",
  industry: "Engineering plastics, alloys and industrial materials",
  summary: "A grade-selection website centered on properties, application fit, technical documents and sample requests.",
  buyerRoles: ["Materials engineer", "R&D engineer", "Technical buyer"],
  status: "ready",
  visualDirection: "Material-first visual system balancing tactile samples with dense property and compliance data.",
  accent: "#14b8a6",
  routes: ["/", "/products", "/products/[slug]", "/categories/[slug]", "/applications", "/certifications", "/resources", "/about", "/rfq"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Material properties and grades map to Product.attributes.",
    "TDS, SDS and revision history require a controlled document adapter before production use.",
  ],
};
