import type { TemplateDemoData } from "@/contracts/forgebase";

export const automationBase = "/templates/industrial-automation";

export const industrialAutomationData: TemplateDemoData = {
  site: {
    companyName: "Kinetra Automation",
    legalNotice: "Demonstration company — not a registered automation integrator or equipment supplier",
    tagline: "Connect the line. Clarify the outcome.",
    description: "A ForgeBase website template for automation integrators and robotic-system providers.",
    email: "automation-demo@example.com",
    phone: "+00 000 000 000",
    location: "Demonstration integration region",
    disclosure: {
      label: "Automation Systems Preview",
      message: "All systems, performance figures, outcomes, certifications and company details are illustrative.",
    },
  },
  ctas: [
    { id: "automation-nav-contact", label: "Book a consultation", href: `${automationBase}/contact/`, intent: "book_meeting", variant: "primary" },
    { id: "automation-diagnostic", label: "Diagnose your line", href: `${automationBase}/contact/`, intent: "book_meeting", variant: "primary" },
    { id: "automation-solutions", label: "Explore solutions", href: `${automationBase}/solutions/`, intent: "view_product", variant: "secondary" },
    { id: "automation-case-studies", label: "Review outcomes", href: `${automationBase}/case-studies/`, intent: "view_product", variant: "text" },
    { id: "automation-submit", label: "Prepare consultation brief", href: `${automationBase}/contact/`, intent: "book_meeting", variant: "primary" },
  ],
  categories: [
    { id: "cat-robotics", slug: "robotic-cells", name: "Robotic cells", description: "Guarded automation concepts for repetitive machine and material-handling tasks." },
    { id: "cat-vision", slug: "vision-quality", name: "Vision & quality", description: "Inline inspection concepts that connect decisions, rejection logic and traceability." },
    { id: "cat-assembly", slug: "flexible-assembly", name: "Flexible assembly", description: "Recipe-driven cells for mixed-model assembly and error-proofed handoffs." },
  ],
  products: [
    {
      id: "solution-tend-r1",
      slug: "robotic-machine-tending",
      name: "KINETRA TEND / R1",
      modelNumber: "R1 CELL CONCEPT",
      shortDescription: "A fictional guarded machine-tending cell concept connecting workpiece presentation, robot handling and machine-cycle signals.",
      categoryId: "cat-robotics",
      attributes: [
        { label: "Machine interface", value: "Demo OPC UA + discrete I/O" },
        { label: "Payload envelope", value: "Illustrative 12 kg" },
        { label: "Changeover", value: "Demo recipe + gripper cart" },
        { label: "Data boundary", value: "Cell events to line historian" },
      ],
      applications: ["CNC tending", "Inspection handoff", "Labor-constrained operations"],
      cta: { id: "automation-tend-view", label: "Explore TEND / R1", href: `${automationBase}/solutions/robotic-machine-tending/`, intent: "view_product" },
    },
    {
      id: "solution-vision-q2",
      slug: "machine-vision-inspection",
      name: "KINETRA VISION / Q2",
      modelNumber: "Q2 INSPECTION CONCEPT",
      shortDescription: "A fictional inline vision concept connecting controlled imaging, decision rules, rejection and record context.",
      categoryId: "cat-vision",
      attributes: [
        { label: "Inspection rate", value: "Illustrative 45 parts/min" },
        { label: "Camera topology", value: "Demo dual-view station" },
        { label: "Reject logic", value: "PLC-confirmed divert" },
        { label: "Traceability", value: "Result + recipe + timestamp" },
      ],
      applications: ["Presence checks", "Surface review", "Assembly verification"],
      cta: { id: "automation-vision-view", label: "Explore VISION / Q2", href: `${automationBase}/solutions/machine-vision-inspection/`, intent: "view_product" },
    },
    {
      id: "solution-flex-a3",
      slug: "flexible-assembly-cell",
      name: "KINETRA FLEX / A3",
      modelNumber: "A3 ASSEMBLY CONCEPT",
      shortDescription: "A fictional mixed-model assembly cell concept with recipe control, guided verification and structured station handoffs.",
      categoryId: "cat-assembly",
      attributes: [
        { label: "Station count", value: "Illustrative 3 modules" },
        { label: "Recipe model", value: "Demo variant routing" },
        { label: "Error proofing", value: "Vision + torque confirmation" },
        { label: "Line handoff", value: "MES-ready event boundary" },
      ],
      applications: ["Mixed-model assembly", "Variant routing", "Quality-gated handoff"],
      cta: { id: "automation-flex-view", label: "Explore FLEX / A3", href: `${automationBase}/solutions/flexible-assembly-cell/`, intent: "view_product" },
    },
  ],
  applications: [
    { id: "app-tending", slug: "labor-constrained-tending", name: "Labor-constrained tending", description: "Map repetitive loading, dwell time and operator travel before selecting robot reach or payload." },
    { id: "app-inspection", slug: "inline-inspection", name: "Inline inspection", description: "Define the defect decision, image conditions and reject confirmation before choosing camera hardware." },
    { id: "app-assembly", slug: "mixed-model-assembly", name: "Mixed-model assembly", description: "Coordinate recipes, verification and handoffs across variants without hiding process exceptions." },
  ],
  capabilities: [
    { id: "cap-discovery", slug: "discovery-simulation", name: "Discovery & simulation", description: "Frame the operating constraint, process states and acceptance test before detailed design.", metrics: [{ label: "Demo gate", value: "Concept review" }] },
    { id: "cap-controls", slug: "controls-integration", name: "Controls & integration", description: "Connect machine signals, safety functions, cell control and production-data boundaries.", metrics: [{ label: "Demo layers", value: "4 integration layers" }] },
    { id: "cap-lifecycle", slug: "commissioning-lifecycle", name: "Commissioning & lifecycle", description: "Structure factory acceptance, site validation, training and change control as visible deliverables.", metrics: [{ label: "Demo handoff", value: "FAT → SAT → support" }] },
  ],
  certifications: [
    { id: "cert-safety", name: "Example machine-safety review record", scope: "Demonstration only — no safety validation or compliance is claimed", demoOnly: true },
    { id: "cert-controls", name: "Example controls acceptance record", scope: "Illustrative test structure without an approved installation", demoOnly: true },
    { id: "cert-training", name: "Example operator-training record", scope: "Demonstration content only — no training was delivered", demoOnly: true },
  ],
  faqs: [
    { id: "faq-01", question: "Are these operating automation systems?", answer: "No. The systems, interfaces and performance figures are fictional examples for demonstrating the website experience." },
    { id: "faq-02", question: "Will the consultation form contact anyone?", answer: "No. The static preview processes the interaction locally and creates no meeting, lead, contact record or email." },
  ],
  rfqFields: [
    { id: "bottleneck", label: "Primary line constraint", type: "select", required: true, options: ["Labor coverage", "Quality escapes", "Cycle-time variation", "Mixed-model complexity"], forgeBaseField: "custom_fields.primary_constraint" },
    { id: "process", label: "Current process", type: "text", required: true, placeholder: "Example: operator loads two CNC machines", forgeBaseField: "custom_fields.current_process" },
    { id: "layer", label: "Integration boundary", type: "select", required: true, options: ["Standalone cell", "Existing machine / PLC", "Line controls", "MES / production data"], forgeBaseField: "custom_fields.integration_boundary" },
    { id: "name", label: "Name", type: "text", required: true, placeholder: "Your name", forgeBaseField: "full_name" },
    { id: "email", label: "Work email", type: "email", required: true, placeholder: "name@company.com", forgeBaseField: "email" },
    { id: "company", label: "Company", type: "text", required: true, placeholder: "Company name", forgeBaseField: "company_name" },
    { id: "timeline", label: "Decision horizon", type: "select", required: true, options: ["Exploring", "Within 6 months", "Within 12 months", "Budget cycle unknown"], forgeBaseField: "custom_fields.timeline" },
    { id: "message", label: "Line context", type: "textarea", required: true, placeholder: "Volumes, variants, constraints and what a successful outcome would change", forgeBaseField: "message" },
  ],
};

export const automationCases = [
  { code: "FLOW / 01", title: "Machine-tending flow concept", sector: "Precision production", before: "Operators split attention across loading, inspection and material movement.", after: "A fictional future-state map coordinates presentation, robot handling and confirmed machine state.", outcome: "Illustrative 22% less operator travel", boundary: "Scenario only — not a measured customer result" },
  { code: "FLOW / 02", title: "Inline inspection concept", sector: "Component assembly", before: "End-of-line sampling delays defect feedback and obscures the process source.", after: "A fictional inspection gate links image conditions, decision rules and a confirmed reject event.", outcome: "Illustrative same-cycle feedback", boundary: "Scenario only — not a production claim" },
  { code: "FLOW / 03", title: "Mixed-model handoff concept", sector: "Electromechanical assembly", before: "Variant changes rely on disconnected work instructions and manual confirmation.", after: "A fictional recipe layer coordinates guided assembly, verification and traceable station release.", outcome: "Illustrative 3-model routing", boundary: "Scenario only — not a deployed system" },
] as const;

export const integrationLayers = [
  { code: "L4", name: "Production context", detail: "MES orders, identifiers and approved reporting boundaries." },
  { code: "L3", name: "Line coordination", detail: "Routing, buffering, recipe state and line-level exceptions." },
  { code: "L2", name: "Cell control", detail: "PLC sequence, safety state, robot tasks and inspection decisions." },
  { code: "L1", name: "Physical process", detail: "Parts, tooling, sensors, guarding and machine interfaces." },
] as const;
