import type { TemplateDemoData } from "@/contracts/forgebase";

export const industrialBase = "/templates/industrial-machinery";

export const industrialMachineryData: TemplateDemoData = {
  site: {
    companyName: "Vantera Systems",
    legalNotice: "Demonstration company — not a registered equipment manufacturer",
    tagline: "Production systems specified around output, integration and lifetime support.",
    description: "A ForgeBase website template for industrial equipment manufacturers and production-system integrators.",
    email: "systems-demo@example.com",
    phone: "+00 000 000 000",
    location: "Demonstration service region",
    disclosure: {
      label: "Equipment Template Preview",
      message: "All equipment, performance figures, locations and service claims are illustrative.",
    },
  },
  ctas: [
    { id: "machinery-nav-rfq", label: "Scope a system", href: `${industrialBase}/rfq/`, intent: "request_quote", variant: "primary" },
    { id: "machinery-hero-rfq", label: "Configure your line", href: `${industrialBase}/rfq/`, intent: "request_quote", variant: "primary" },
    { id: "machinery-compare", label: "Compare systems", href: `${industrialBase}/products/`, intent: "view_product", variant: "secondary" },
    { id: "machinery-applications", label: "Review an application", href: `${industrialBase}/applications/`, intent: "view_product", variant: "text" },
    { id: "machinery-service", label: "Discuss service coverage", href: `${industrialBase}/rfq/`, intent: "contact_sales", variant: "text" },
    { id: "machinery-resource", label: "Review technical resources", href: `${industrialBase}/resources/#resource-demo-note`, intent: "download_spec", variant: "text" },
    { id: "machinery-submit", label: "Request system review", href: `${industrialBase}/rfq/`, intent: "request_quote", variant: "primary" },
  ],
  categories: [
    { id: "cat-forming", slug: "forming-systems", name: "Forming Systems", description: "Servo-controlled press and feed concepts." },
    { id: "cat-processing", slug: "processing-cells", name: "Processing Cells", description: "Enclosed flexible cutting and finishing concepts." },
    { id: "cat-handling", slug: "handling-automation", name: "Handling Automation", description: "Modular part movement and tending concepts." },
  ],
  products: [
    {
      id: "machine-01",
      slug: "forma-s420",
      name: "FORMA S420",
      modelNumber: "DEMO-S420",
      shortDescription: "A fictional servo forming platform for programmable motion and repeatable changeovers.",
      categoryId: "cat-forming",
      attributes: [
        { label: "Nominal force", value: "Demo 420 kN" },
        { label: "Stroke", value: "Demo 250 mm" },
        { label: "Rated speed", value: "Demo up to 80 spm" },
      ],
      applications: ["Metal enclosures", "Mobility components"],
      cta: { id: "machine-forma-view", label: "Explore FORMA S420", href: `${industrialBase}/products/forma-s420/`, intent: "view_product" },
    },
    {
      id: "machine-02",
      slug: "laser-lx8",
      name: "LASER LX8",
      modelNumber: "DEMO-LX8",
      shortDescription: "An enclosed flexible-processing concept for mixed geometry and short production runs.",
      categoryId: "cat-processing",
      attributes: [
        { label: "Work area", value: "Demo 1500 × 3000 mm" },
        { label: "Power concept", value: "Demo 6 kW" },
        { label: "Changeover", value: "Program-led" },
      ],
      applications: ["Industrial cabinets", "Appliance panels"],
      cta: { id: "machine-laser-view", label: "Explore LASER LX8", href: `${industrialBase}/products/laser-lx8/`, intent: "view_product" },
    },
    {
      id: "machine-03",
      slug: "motion-m6",
      name: "MOTION M6",
      modelNumber: "DEMO-M6",
      shortDescription: "A modular robotic handling cell concept for machine tending and controlled part flow.",
      categoryId: "cat-handling",
      attributes: [
        { label: "Payload", value: "Demo 35 kg" },
        { label: "Reach", value: "Demo 2050 mm" },
        { label: "Cell format", value: "Modular" },
      ],
      applications: ["Machine tending", "End-of-line handling"],
      cta: { id: "machine-motion-view", label: "Explore MOTION M6", href: `${industrialBase}/products/motion-m6/`, intent: "view_product" },
    },
  ],
  applications: [
    { id: "app-enclosure", slug: "metal-enclosures", name: "Metal enclosures", description: "Forming, processing and handling concepts organized around finish-critical panels and repeatable changeovers." },
    { id: "app-mobility", slug: "mobility-components", name: "Mobility components", description: "Production-cell concepts for traceable forming and controlled flow of structural subcomponents." },
    { id: "app-appliance", slug: "appliance-production", name: "Appliance production", description: "Flexible equipment concepts for high-mix panel families and model-driven setup changes." },
  ],
  capabilities: [
    { id: "cap-feasibility", slug: "feasibility-engineering", name: "Feasibility engineering", description: "Part, process and target-rate inputs are converted into a transparent concept boundary.", metrics: [{ label: "Output", value: "Concept brief" }] },
    { id: "cap-integration", slug: "line-integration", name: "Line integration", description: "Material flow, guarding, controls and upstream or downstream interfaces are considered together.", metrics: [{ label: "Scope", value: "Cell to line" }] },
    { id: "cap-validation", slug: "validation-handover", name: "Validation & handover", description: "Acceptance criteria, operator readiness and service documentation form the handover plan.", metrics: [{ label: "Evidence", value: "FAT / SAT concepts" }] },
  ],
  certifications: [
    { id: "cert-risk", name: "Example machinery risk-assessment workflow", scope: "Demonstration only — no conformity or certification is claimed", demoOnly: true },
    { id: "cert-acceptance", name: "Example acceptance documentation", scope: "Illustrative FAT and SAT planning structure", demoOnly: true },
  ],
  faqs: [
    { id: "faq-01", question: "Can I send a part and target rate?", answer: "The production version can attach files and process inputs to a ForgeBase RFQ. This preview never uploads or stores them." },
    { id: "faq-02", question: "Are the machine specifications real?", answer: "No. Every model and performance figure is fictional and exists only to demonstrate the website structure." },
  ],
  rfqFields: [
    { id: "name", label: "Name", type: "text", required: true, placeholder: "Your name", forgeBaseField: "full_name" },
    { id: "email", label: "Work email", type: "email", required: true, placeholder: "name@company.com", forgeBaseField: "email" },
    { id: "company", label: "Company", type: "text", required: true, placeholder: "Company name", forgeBaseField: "company_name" },
    { id: "system", label: "System interest", type: "select", required: true, options: ["Forming system", "Processing cell", "Handling automation", "Not sure yet"], forgeBaseField: "custom_fields.system_interest" },
    { id: "material", label: "Workpiece / material", type: "text", placeholder: "Part family and material", forgeBaseField: "custom_fields.workpiece" },
    { id: "rate", label: "Target production rate", type: "text", placeholder: "Units per minute, hour or shift", forgeBaseField: "custom_fields.target_rate" },
    { id: "attachment", label: "Requirement brief", type: "file", forgeBaseField: "attachments" },
    { id: "message", label: "Project requirements", type: "textarea", required: true, placeholder: "Current process, constraints, timing and success criteria", forgeBaseField: "message" },
  ],
};

export const industrialServices = [
  { number: "01", name: "Application study", description: "Translate workpiece, rate, quality and staffing inputs into an equipment concept boundary." },
  { number: "02", name: "Installation planning", description: "Make utilities, floor space, logistics, guarding and commissioning dependencies visible early." },
  { number: "03", name: "Lifecycle support", description: "Structure preventive maintenance, spare-parts planning, training and remote-support expectations." },
] as const;

export const industrialResources = [
  { code: "R-01", title: "System qualification checklist", format: "PDF concept", description: "The information a buyer should assemble before requesting a line concept." },
  { code: "R-02", title: "FAT / SAT planning guide", format: "PDF concept", description: "An illustrative acceptance framework for project alignment." },
  { code: "R-03", title: "Utility planning worksheet", format: "XLS concept", description: "A future downloadable worksheet for power, air, floor and connectivity inputs." },
] as const;
