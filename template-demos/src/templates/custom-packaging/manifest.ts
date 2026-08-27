import type { TemplateManifest } from "@/contracts/forgebase";

export const customPackagingManifest: TemplateManifest = {
  slug: "custom-packaging",
  name: "Custom Packaging Manufacturing",
  industry: "Custom industrial and retail packaging",
  summary: "A configuration-led website for dimensions, materials, print, MOQ, sampling and volume-based quotation.",
  buyerRoles: ["Packaging engineer", "Brand operations manager", "Procurement manager"],
  status: "ready",
  visualDirection: "Material-rich modular layouts with packaging configurations, dielines and quantity-driven conversion.",
  accent: "#eab308",
  routes: ["/", "/products", "/products/[slug]", "/applications", "/capabilities", "/about", "/rfq"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Dimensions, material, printing, finish and MOQ map to Product.attributes and RFQ custom fields.",
    "Interactive dieline generation is outside the static Demo scope and requires future product work.",
  ],
};
