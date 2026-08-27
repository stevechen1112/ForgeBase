import type { TemplateDemoData } from "@/contracts/forgebase";

export const electronicsBase = "/templates/electronic-components";

export const electronicComponentsData: TemplateDemoData = {
  site: {
    companyName: "Veltrix Components",
    legalNotice: "Demonstration company — not a registered component manufacturer or distributor",
    tagline: "Parametric component discovery for engineers who need a defensible shortlist.",
    description: "A ForgeBase website template for electronic-component manufacturers and technical distributors.",
    email: "components-demo@example.com",
    phone: "+00 000 000 000",
    location: "Demonstration fulfilment region",
    disclosure: {
      label: "Component Catalogue Preview",
      message: "All parts, specifications, availability, compliance statements and documents are illustrative.",
    },
  },
  ctas: [
    { id: "electronics-nav-sample", label: "Request samples", href: `${electronicsBase}/rfq/`, intent: "request_sample", variant: "primary" },
    { id: "electronics-browse", label: "Browse all parts", href: `${electronicsBase}/products/`, intent: "view_product", variant: "primary" },
    { id: "electronics-datasheet", label: "View Demo datasheets", href: `${electronicsBase}/resources/#datasheet-demo-note`, intent: "download_spec", variant: "secondary" },
    { id: "electronics-application", label: "Explore design contexts", href: `${electronicsBase}/applications/`, intent: "view_product", variant: "text" },
    { id: "electronics-quality", label: "Review quality framework", href: `${electronicsBase}/certifications/`, intent: "view_product", variant: "text" },
    { id: "electronics-submit", label: "Request sample review", href: `${electronicsBase}/rfq/`, intent: "request_sample", variant: "primary" },
  ],
  categories: [
    { id: "cat-connectors", slug: "board-to-board-connectors", name: "Board-to-board connectors", description: "Fine-pitch interconnect concepts for compact stacked assemblies." },
    { id: "cat-protection", slug: "circuit-protection", name: "Circuit protection", description: "Low-capacitance protection-device concepts for exposed signal interfaces." },
    { id: "cat-sensors", slug: "current-sensors", name: "Current sensors", description: "Isolated current-measurement concepts for power and motor-control designs." },
  ],
  products: [
    {
      id: "part-vcx040",
      slug: "vcx-040-mezzanine",
      name: "VCX-040 Mezzanine",
      modelNumber: "VCX-040-40P",
      shortDescription: "A fictional 0.40 mm pitch, 40-position board-to-board connector for compact control assemblies.",
      categoryId: "cat-connectors",
      attributes: [
        { label: "Pitch", value: "Demo 0.40 mm" },
        { label: "Positions", value: "Demo 40" },
        { label: "Stack height", value: "Demo 3.0 mm" },
        { label: "Rated current", value: "Demo 0.5 A" },
        { label: "Temperature", value: "Demo −40 to 125 °C" },
      ],
      applications: ["Compact controllers", "Industrial sensing"],
      cta: { id: "part-vcx040-view", label: "View VCX-040", href: `${electronicsBase}/products/vcx-040-mezzanine/`, intent: "view_product" },
    },
    {
      id: "part-vpt24",
      slug: "vpt-24s-protection-array",
      name: "VPT-24S Protection Array",
      modelNumber: "VPT-24S-06",
      shortDescription: "A fictional low-capacitance transient-protection array for industrial communication interfaces.",
      categoryId: "cat-protection",
      attributes: [
        { label: "Working voltage", value: "Demo 24 V" },
        { label: "Capacitance", value: "Demo 1.0 pF" },
        { label: "Peak pulse", value: "Demo 120 W" },
        { label: "Package", value: "Demo SOT-23-6" },
        { label: "Temperature", value: "Demo −55 to 150 °C" },
      ],
      applications: ["Industrial I/O", "Communication ports"],
      cta: { id: "part-vpt24-view", label: "View VPT-24S", href: `${electronicsBase}/products/vpt-24s-protection-array/`, intent: "view_product" },
    },
    {
      id: "part-vhs50",
      slug: "vhs-50a-current-sensor",
      name: "VHS-50A Current Sensor",
      modelNumber: "VHS-050-A",
      shortDescription: "A fictional isolated Hall-effect current-sensor module for compact power-conversion systems.",
      categoryId: "cat-sensors",
      attributes: [
        { label: "Current range", value: "Demo ±50 A" },
        { label: "Isolation", value: "Demo 2.5 kVrms" },
        { label: "Bandwidth", value: "Demo 120 kHz" },
        { label: "Supply", value: "Demo 5 V" },
        { label: "Temperature", value: "Demo −40 to 105 °C" },
      ],
      applications: ["Motor drives", "Power conversion"],
      cta: { id: "part-vhs50-view", label: "View VHS-50A", href: `${electronicsBase}/products/vhs-50a-current-sensor/`, intent: "view_product" },
    },
  ],
  applications: [
    { id: "app-control", slug: "industrial-control", name: "Industrial control", description: "Compact interconnect, protected I/O and current feedback concepts organized around control-board design constraints." },
    { id: "app-power", slug: "power-conversion", name: "Power conversion", description: "Isolated measurement and protection concepts for converters, drives and distributed power assemblies." },
    { id: "app-sensing", slug: "connected-sensing", name: "Connected sensing", description: "Fine-pitch interconnect and protected communication concepts for distributed industrial sensing nodes." },
  ],
  capabilities: [
    { id: "cap-parametric", slug: "parametric-data", name: "Normalized parametric data", description: "Comparable electrical, mechanical and environmental attributes support engineering search.", metrics: [{ label: "Demo schema", value: "5 attributes / SKU" }] },
    { id: "cap-documents", slug: "document-control", name: "Document control", description: "Datasheet, model and compliance records require visible revision and approval context.", metrics: [{ label: "Demo state", value: "No live files" }] },
  ],
  certifications: [
    { id: "cert-rohs", name: "Example RoHS evidence record", scope: "Demonstration only — no material compliance is claimed", demoOnly: true },
    { id: "cert-reach", name: "Example REACH evidence record", scope: "Illustrative supplier-document structure", demoOnly: true },
    { id: "cert-aec", name: "Example qualification record", scope: "No AEC-Q or other qualification status is claimed", demoOnly: true },
  ],
  faqs: [
    { id: "faq-01", question: "Are these orderable part numbers?", answer: "No. Every part number, specification and availability state is fictional and exists only to demonstrate the catalogue interface." },
    { id: "faq-02", question: "Will a sample request be sent?", answer: "No. This static preview intercepts the request locally and creates no contact, lead, order or email." },
  ],
  rfqFields: [
    { id: "part", label: "Part number", type: "select", required: true, options: ["VCX-040-40P", "VPT-24S-06", "VHS-050-A", "Help me select"], forgeBaseField: "custom_fields.part_number" },
    { id: "quantity", label: "Sample quantity", type: "select", required: true, options: ["5 pieces", "10 pieces", "25 pieces", "Discuss quantity"], forgeBaseField: "custom_fields.sample_quantity" },
    { id: "stage", label: "Design stage", type: "select", required: true, options: ["Architecture", "Prototype", "Validation", "Pre-production"], forgeBaseField: "custom_fields.design_stage" },
    { id: "name", label: "Name", type: "text", required: true, placeholder: "Your name", forgeBaseField: "full_name" },
    { id: "email", label: "Work email", type: "email", required: true, placeholder: "name@company.com", forgeBaseField: "email" },
    { id: "company", label: "Company", type: "text", required: true, placeholder: "Company name", forgeBaseField: "company_name" },
    { id: "message", label: "Design requirements", type: "textarea", required: true, placeholder: "Interface, operating conditions, target timing and qualification needs", forgeBaseField: "message" },
  ],
};

export const electronicsResources = [
  { code: "DS-040", type: "Datasheet concept", title: "VCX-040 technical data", revision: "Demo Rev A", description: "Mechanical envelope, electrical ratings and mating guidance interface." },
  { code: "DS-024", type: "Datasheet concept", title: "VPT-24S technical data", revision: "Demo Rev B", description: "Electrical characteristics, clamping curves and package interface." },
  { code: "AN-050", type: "Application note concept", title: "Current sensing layout guide", revision: "Demo Rev A", description: "Illustrative placement, isolation and thermal-review structure." },
] as const;

export const electronicsAvailability = [
  { part: "VCX-040-40P", status: "Demo sample", lead: "Illustrative 4 weeks" },
  { part: "VPT-24S-06", status: "Demo sample", lead: "Illustrative 2 weeks" },
  { part: "VHS-050-A", status: "Concept only", lead: "No availability claim" },
] as const;
