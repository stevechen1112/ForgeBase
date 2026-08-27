import type { TemplateManifest } from "@/contracts/forgebase";

export const industrialAutomationManifest: TemplateManifest = {
  slug: "industrial-automation",
  name: "Industrial Automation & Robotics",
  industry: "Automation integration and robotic systems",
  summary: "A solution-led website connecting operational problems, system architecture and consultation conversion.",
  buyerRoles: ["Automation engineer", "Manufacturing engineering manager", "Plant director"],
  status: "ready",
  visualDirection: "Systems-diagram storytelling with application flows, integration layers and measured outcomes.",
  accent: "#7c5cff",
  routes: ["/", "/solutions", "/solutions/[slug]", "/applications", "/capabilities", "/case-studies", "/about", "/contact"],
  forgeBaseEntities: ["SiteProfile", "ProductCategory", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"],
  customDataNotes: [
    "Solution pages compose Application, Product and Capability records.",
    "Case studies require either a documented custom content type or a future standard ForgeBase entity.",
  ],
};
