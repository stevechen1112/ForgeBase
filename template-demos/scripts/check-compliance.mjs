import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const sourceRoot = path.join(root, "src");
const failures = [];
const validCTAIntents = new Set(["view_product", "request_quote", "contact_sales", "download_spec", "request_sample", "book_meeting", "ask_question"]);

const readyTemplates = [
  {
    slug: "precision-machining",
    name: "Precision Machining",
    pages: ["index.html", "products/index.html", "products/servo-housing/index.html", "products/sensor-sleeve/index.html", "products/robot-joint/index.html", "capabilities/index.html", "applications/index.html", "quality/index.html", "about/index.html", "rfq/index.html"],
    assets: ["hero-cnc-facility.png", "capability-five-axis-machining.png", "quality-cmm-inspection.png", "parts-precision-components.png"],
    submitId: "rfq-submit",
    submitIntent: "request_quote",
    requestPage: "rfq/index.html",
    requestHref: "/rfq/",
    componentFiles: ["src/templates/precision-machining/components/PrecisionMachiningTemplate.tsx", "src/templates/precision-machining/components/PrecisionSitePages.tsx"],
  },
  {
    slug: "industrial-machinery",
    name: "Industrial Machinery",
    pages: ["index.html", "products/index.html", "products/forma-s420/index.html", "products/laser-lx8/index.html", "products/motion-m6/index.html", "applications/index.html", "capabilities/index.html", "services/index.html", "resources/index.html", "about/index.html", "rfq/index.html"],
    assets: ["hero-servo-forming-line.png", "equipment-family.png", "coil-forming-process.png", "field-service-maintenance.png", "social-preview.png"],
    submitId: "machinery-submit",
    submitIntent: "request_quote",
    requestPage: "rfq/index.html",
    requestHref: "/rfq/",
    componentFiles: ["src/templates/industrial-machinery/components/MachinerySite.tsx", "src/templates/industrial-machinery/components/SystemConfigurator.tsx"],
  },
  {
    slug: "electronic-components",
    name: "Electronic Components",
    pages: ["index.html", "products/index.html", "products/vcx-040-mezzanine/index.html", "products/vpt-24s-protection-array/index.html", "products/vhs-50a-current-sensor/index.html", "categories/board-to-board-connectors/index.html", "categories/circuit-protection/index.html", "categories/current-sensors/index.html", "applications/index.html", "certifications/index.html", "resources/index.html", "about/index.html", "rfq/index.html"],
    assets: ["component-family-hero.png", "mezzanine-connector-macro.png", "protection-device-reel.png", "component-validation-lab.png", "social-preview.png"],
    submitId: "electronics-submit",
    submitIntent: "request_sample",
    requestPage: "rfq/index.html",
    requestHref: "/rfq/",
    componentFiles: ["src/templates/electronic-components/components/ElectronicSite.tsx", "src/templates/electronic-components/components/ParametricCatalog.tsx", "src/templates/electronic-components/components/SampleRequest.tsx"],
  },
  {
    slug: "industrial-automation",
    name: "Industrial Automation",
    pages: ["index.html", "solutions/index.html", "solutions/robotic-machine-tending/index.html", "solutions/machine-vision-inspection/index.html", "solutions/flexible-assembly-cell/index.html", "applications/index.html", "capabilities/index.html", "case-studies/index.html", "about/index.html", "contact/index.html"],
    assets: ["connected-robotic-line.png", "robotic-machine-tending.png", "machine-vision-inspection.png", "automation-commissioning.png", "social-preview.png"],
    submitId: "automation-submit",
    submitIntent: "book_meeting",
    requestPage: "contact/index.html",
    requestHref: "/contact/",
    componentFiles: ["src/templates/industrial-automation/components/AutomationSite.tsx", "src/templates/industrial-automation/components/AutomationMap.tsx", "src/templates/industrial-automation/components/SolutionDiagnostic.tsx"],
  },
  {
    slug: "engineering-materials",
    name: "Engineering Materials",
    pages: ["index.html", "products/index.html", "products/therma-px-620/index.html", "products/aerion-a7-58/index.html", "products/cerava-c9-94/index.html", "categories/performance-polymers/index.html", "categories/lightweight-alloys/index.html", "categories/technical-ceramics/index.html", "applications/index.html", "resources/index.html", "certifications/index.html", "about/index.html", "rfq/index.html"],
    assets: ["material-archive-hero.png", "performance-polymers.png", "lightweight-alloys.png", "technical-ceramics.png", "materials-testing-lab.png", "social-preview.png"],
    submitId: "materials-submit",
    submitIntent: "request_sample",
    requestPage: "rfq/index.html",
    requestHref: "/rfq/",
    componentFiles: ["src/templates/engineering-materials/components/MaterialsSite.tsx", "src/templates/engineering-materials/components/MaterialLens.tsx", "src/templates/engineering-materials/components/SampleBrief.tsx"],
  },
  {
    slug: "custom-packaging",
    name: "Custom Packaging",
    pages: ["index.html", "products/index.html", "products/ship-s1-mailer/index.html", "products/fold-f2-carton/index.html", "products/present-r3-rigid-box/index.html", "applications/index.html", "capabilities/index.html", "about/index.html", "rfq/index.html"],
    assets: ["packaging-system-hero.png", "corrugated-mailers.png", "folding-cartons.png", "rigid-boxes.png", "packaging-prototyping.png", "social-preview.png"],
    submitId: "packaging-submit",
    submitIntent: "request_quote",
    requestPage: "rfq/index.html",
    requestHref: "/rfq/",
    componentFiles: ["src/templates/custom-packaging/components/PackagingSite.tsx", "src/templates/custom-packaging/components/PackConfigurator.tsx"],
  },
];

function requireCondition(condition, message) {
  if (!condition) failures.push(message);
}

async function read(relativePath) {
  return readFile(path.join(root, relativePath), "utf8");
}

async function collectFiles(directory) {
  const entries = await readdir(directory, { withFileTypes: true });
  const nested = await Promise.all(entries.map((entry) => {
    const target = path.join(directory, entry.name);
    return entry.isDirectory() ? collectFiles(target) : [target];
  }));
  return nested.flat();
}

const routeSource = await read("src/app/templates/[templateSlug]/page.tsx");
requireCondition(!/templateSlug\s*===|switch\s*\(\s*templateSlug/.test(routeSource), "Template renderer must be registry-driven; slug conditionals are forbidden.");
requireCondition(routeSource.includes("getRegisteredTemplate"), "Template route must resolve its renderer through the registry.");

const rfqSource = await read("src/components/DemoRFQForm.tsx");
requireCondition(rfqSource.includes("event.preventDefault()"), "Demo RFQ must intercept submission locally.");
requireCondition(!/tabIndex=\{?-1\}?/.test(rfqSource), "Interactive RFQ controls must remain keyboard-focusable.");
requireCondition(rfqSource.includes("data-cta-intent"), "RFQ submission must expose a CTA intent.");

const sourceFiles = (await collectFiles(sourceRoot)).filter((file) => /\.(ts|tsx|js|jsx)$/.test(file));
const forbiddenSideEffects = [
  [/(^|[^\w])fetch\s*\(/, "network fetch"],
  [/XMLHttpRequest/, "XMLHttpRequest"],
  [/sendBeacon/, "sendBeacon"],
  [/localStorage|sessionStorage/, "browser persistence"],
  [/gtag\s*\(|posthog|analytics\.track|fbq\s*\(/i, "visitor tracking"],
];

for (const file of sourceFiles) {
  const content = await readFile(file, "utf8");
  for (const [pattern, label] of forbiddenSideEffects) {
    requireCondition(!pattern.test(content), `${path.relative(root, file)} contains forbidden ${label}.`);
  }
}

let checkedPageCount = 0;

for (const template of readyTemplates) {
  const manifestSource = await read(`src/templates/${template.slug}/manifest.ts`);
  requireCondition(manifestSource.includes('status: "ready"'), `${template.name} manifest must explicitly declare ready status.`);
  requireCondition(manifestSource.includes('"/applications"'), `${template.name} must use the standard /applications route.`);
  requireCondition(!manifestSource.includes('"/industries"'), `${template.name} must not use the deprecated /industries route.`);
  for (const entity of ["SiteProfile", "Product", "Application", "Capability", "Certification", "FAQItem", "CTA", "RFQ"]) {
    requireCondition(manifestSource.includes(`"${entity}"`), `${template.name} manifest must declare the ${entity} entity.`);
  }

  for (const componentFile of template.componentFiles) {
    const source = await read(componentFile);
    requireCondition(!/href=\{[^}]*(?:\/rfq\/|\/contact\/)/.test(source), `${componentFile} contains a direct request href; use a typed DemoCTA.`);
  }

  const outputRoot = path.join(root, "out", "templates", template.slug);
  for (const relativePage of template.pages) {
    checkedPageCount += 1;
    let html = "";
    try {
      html = await readFile(path.join(outputRoot, relativePage), "utf8");
    } catch {
      failures.push(`${template.name} is missing static page: ${relativePage}`);
      continue;
    }

    requireCondition(/name="robots" content="noindex, nofollow"/.test(html), `${template.slug}/${relativePage} must be noindex, nofollow.`);
    requireCondition(html.includes("Template Preview"), `${template.slug}/${relativePage} must display the Demo disclosure.`);
    requireCondition(!html.includes("Template Preview — Template Preview"), `${template.slug}/${relativePage} duplicates the Demo disclosure label.`);
    requireCondition(!/<form[^>]+action=["']https?:/i.test(html), `${template.slug}/${relativePage} contains an external form action.`);

    const requestPattern = new RegExp(`<a\\b[^>]*href="[^"]*${template.requestHref.replaceAll("/", "\\/")}[^"]*"[^>]*>`, "g");
    const requestLinks = html.match(requestPattern) ?? [];
    for (const link of requestLinks) {
      requireCondition(link.includes("data-cta-id="), `${template.slug}/${relativePage} contains a request link without CTA id metadata.`);
      requireCondition(link.includes("data-cta-intent="), `${template.slug}/${relativePage} contains a request link without CTA intent metadata.`);
    }

    const intentValues = [...html.matchAll(/data-cta-intent="([^"]+)"/g)].map((match) => match[1]);
    for (const intent of intentValues) requireCondition(validCTAIntents.has(intent), `${template.slug}/${relativePage} uses invalid CTA intent: ${intent}.`);
  }

  const rfqHtml = await readFile(path.join(outputRoot, template.requestPage), "utf8");
  const submitButtonPattern = new RegExp(`<button(?=[^>]*data-cta-id="${template.submitId}")(?=[^>]*data-cta-intent="${template.submitIntent}")[^>]*>`);
  requireCondition(submitButtonPattern.test(rfqHtml), `${template.name} RFQ submit button must map its typed CTA id to ${template.submitIntent}.`);

  const assetManifest = await read(`docs/templates/${template.slug}/ASSETS.md`);
  for (const asset of template.assets) requireCondition(assetManifest.includes(asset), `${template.name} asset manifest is missing ${asset}.`);
}

if (failures.length) {
  console.error("ForgeBase template compliance failed:\n");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`ForgeBase template compliance passed (${readyTemplates.length} ready templates, ${checkedPageCount} static pages checked).`);
