import type { TemplateManifest } from "@/contracts/forgebase";

export const precisionMachiningManifest: TemplateManifest = {
  slug: "precision-machining",
  name: "Precision Machining",
  industry: "CNC machining and contract manufacturing",
  summary: "A technical, drawing-first website for sourcing engineers evaluating tolerances, materials, capacity and quality controls.",
  buyerRoles: ["Sourcing engineer", "Commodity manager", "Design engineer"],
  status: "ready",
  visualDirection: "Editorial engineering system with a dark technical grid, dense evidence and drawing-led conversion.",
  accent: "#dbff4a",
  routes: ["/", "/products", "/products/[slug]", "/capabilities", "/applications", "/quality", "/about", "/rfq"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Material, tolerance and finish map to Product.attributes.",
    "The navigation label Industries maps to the standard Application entity and /applications route.",
    "Drawing upload requires a future secure RFQ attachment adapter.",
  ],
};
