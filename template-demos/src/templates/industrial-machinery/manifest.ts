import type { TemplateManifest } from "@/contracts/forgebase";

export const industrialMachineryManifest: TemplateManifest = {
  slug: "industrial-machinery",
  name: "Industrial Machinery",
  industry: "Machinery and production equipment",
  summary: "A configuration-led equipment workspace built around system selection, operating boundaries and lifecycle planning.",
  buyerRoles: ["Plant manager", "Process engineer", "Operations director"],
  status: "ready",
  visualDirection: "Industrial control-console layout with a persistent system rail, equipment records, engineering gates and a stepped project configurator.",
  accent: "#ff6b35",
  routes: ["/", "/products", "/products/[slug]", "/applications", "/capabilities", "/services", "/resources", "/about", "/rfq"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Installation and after-sales coverage map to Capability until a dedicated Service entity exists.",
    "Video and downloadable manuals require a future managed media/document adapter.",
  ],
};
