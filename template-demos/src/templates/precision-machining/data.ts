import type { TemplateDemoData } from "@/contracts/forgebase";

export const precisionMachiningData: TemplateDemoData = {
  site: {
    companyName: "AxisForm Precision",
    legalNotice: "Demonstration company — not a registered manufacturer",
    tagline: "Tight-tolerance parts, documented from drawing to delivery.",
    description: "A ForgeBase website template for CNC machining suppliers serving industrial, mobility and automation buyers.",
    email: "demo@example.com",
    phone: "+00 000 000 000",
    location: "Demonstration location",
    disclosure: {
      label: "Template Preview",
      message: "All names, capabilities, figures and certifications are illustrative.",
    },
  },
  ctas: [
    { id: "nav-rfq", label: "Send a drawing", href: "/templates/precision-machining/rfq/", intent: "request_quote", variant: "primary" },
    { id: "hero-rfq", label: "Send your drawing", href: "/templates/precision-machining/rfq/", intent: "request_quote", variant: "primary" },
    { id: "hero-capabilities", label: "Review capabilities", href: "/templates/precision-machining/capabilities/", intent: "view_product", variant: "secondary" },
    { id: "product-detail-rfq", label: "Review a similar drawing", href: "/templates/precision-machining/rfq/", intent: "request_quote", variant: "primary" },
    { id: "application-rfq", label: "Discuss an application", href: "/templates/precision-machining/rfq/", intent: "ask_question", variant: "text" },
    { id: "conversion-rfq", label: "Open Demo RFQ", href: "/templates/precision-machining/rfq/", intent: "request_quote", variant: "primary" },
    { id: "rfq-submit", label: "Request manufacturing review", href: "/templates/precision-machining/rfq/", intent: "request_quote", variant: "primary" },
  ],
  categories: [
    { id: "cat-turned", slug: "turned-parts", name: "Turned Components" },
    { id: "cat-milled", slug: "milled-parts", name: "Milled Components" },
  ],
  products: [
    {
      id: "part-01", slug: "servo-housing", name: "Servo Drive Housing", modelNumber: "DEMO-M01",
      shortDescription: "Multi-face aluminum housing concept with sealing and bearing features.", categoryId: "cat-milled",
      attributes: [{ label: "Material", value: "Al 6061" }, { label: "Tolerance", value: "±0.015 mm" }, { label: "Finish", value: "Black anodized" }],
      applications: ["Industrial automation"],
      cta: { id: "part-servo-view", label: "Review a similar part", href: "/templates/precision-machining/products/servo-housing/", intent: "view_product" },
    },
    {
      id: "part-02", slug: "sensor-sleeve", name: "Sensor Sleeve", modelNumber: "DEMO-T08",
      shortDescription: "Thin-wall turned component concept designed for concentricity control.", categoryId: "cat-turned",
      attributes: [{ label: "Material", value: "SS 316L" }, { label: "Tolerance", value: "±0.010 mm" }, { label: "Finish", value: "Passivated" }],
      applications: ["Process instrumentation"],
      cta: { id: "part-sensor-view", label: "Discuss tolerance", href: "/templates/precision-machining/products/sensor-sleeve/", intent: "view_product" },
    },
    {
      id: "part-03", slug: "robot-joint", name: "Robot Joint Interface", modelNumber: "DEMO-M14",
      shortDescription: "Five-axis interface part concept with position-critical hole patterns.", categoryId: "cat-milled",
      attributes: [{ label: "Material", value: "Al 7075" }, { label: "Tolerance", value: "GD&T controlled" }, { label: "Finish", value: "Hard anodized" }],
      applications: ["Robotics"],
      cta: { id: "part-robot-view", label: "Review part concept", href: "/templates/precision-machining/products/robot-joint/", intent: "view_product" },
    },
  ],
  applications: [
    { id: "app-auto", slug: "industrial-automation", name: "Industrial automation", description: "Motion, sensing and machine-interface components." },
    { id: "app-mobility", slug: "mobility-systems", name: "Mobility systems", description: "Prototype and production parts for electrified platforms." },
    { id: "app-instrument", slug: "instrumentation", name: "Instrumentation", description: "Compact parts where surfaces and concentricity matter." },
  ],
  capabilities: [
    { id: "cap-5axis", slug: "five-axis-milling", name: "5-axis milling", description: "Single-setup machining concepts for complex geometry.", metrics: [{ label: "Envelope", value: "Demo 600 × 500 × 450 mm" }] },
    { id: "cap-turn", slug: "precision-turning", name: "Precision turning", description: "Turn-mill concepts for concentric, thin-wall features.", metrics: [{ label: "Diameter", value: "Demo Ø3–250 mm" }] },
    { id: "cap-quality", slug: "quality-control", name: "Documented inspection", description: "Illustrative inspection planning, traceability and FAIR workflow.", metrics: [{ label: "Reporting", value: "FAIR / CMM / CoC" }] },
  ],
  certifications: [
    { id: "cert-qms", name: "Example QMS framework", scope: "Demonstration only — no certification is claimed", demoOnly: true },
    { id: "cert-trace", name: "Material traceability workflow", scope: "Illustrative process capability", demoOnly: true },
  ],
  faqs: [
    { id: "faq-01", question: "Can I upload a drawing?", answer: "In this preview the upload control is disabled. A production ForgeBase site can connect secure attachments to RFQ records." },
  ],
  rfqFields: [
    { id: "name", label: "Name", type: "text", required: true, placeholder: "Your name", forgeBaseField: "full_name" },
    { id: "email", label: "Work email", type: "email", required: true, placeholder: "name@company.com", forgeBaseField: "email" },
    { id: "company", label: "Company", type: "text", required: true, placeholder: "Company name", forgeBaseField: "company_name" },
    { id: "stage", label: "Project stage", type: "select", options: ["Prototype", "Pre-production", "Recurring production"], forgeBaseField: "custom_fields.project_stage" },
    { id: "drawing", label: "Drawing", type: "file", forgeBaseField: "attachments" },
    { id: "message", label: "Part requirements", type: "textarea", required: true, placeholder: "Material, tolerance, volume and target timing", forgeBaseField: "message" },
  ],
};
