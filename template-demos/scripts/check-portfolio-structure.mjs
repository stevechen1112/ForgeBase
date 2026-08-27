import { access, readFile } from "node:fs/promises";
import path from "node:path";

const root = process.cwd();
const failures = [];
const templates = [
  { slug: "precision-machining", status: "ready", assets: true },
  { slug: "industrial-machinery", status: "ready", assets: true },
  { slug: "electronic-components", status: "ready", assets: true },
  { slug: "industrial-automation", status: "ready", assets: true },
  { slug: "engineering-materials", status: "ready", assets: true },
  { slug: "custom-packaging", status: "ready", assets: true },
];

async function exists(relativePath) {
  try {
    await access(path.join(root, relativePath));
    return true;
  } catch {
    return false;
  }
}

async function read(relativePath) {
  return readFile(path.join(root, relativePath), "utf8");
}

function requireCondition(condition, message) {
  if (!condition) failures.push(message);
}

const registry = await read("src/templates/registry.ts");
const portfolio = await read("docs/PORTFOLIO.md");

for (const template of templates) {
  const manifestPath = `src/templates/${template.slug}/manifest.ts`;
  const briefPath = `docs/templates/${template.slug}/BRIEF.md`;
  requireCondition(await exists(manifestPath), `${template.slug} is missing manifest.ts.`);
  requireCondition(await exists(briefPath), `${template.slug} is missing BRIEF.md.`);
  requireCondition(registry.includes(`./${template.slug}/manifest`), `${template.slug} manifest is not imported by the registry.`);
  requireCondition(portfolio.includes(`\`${template.slug}\``), `${template.slug} is missing from PORTFOLIO.md.`);

  if (await exists(manifestPath)) {
    const manifest = await read(manifestPath);
    requireCondition(manifest.includes(`slug: "${template.slug}"`), `${template.slug} manifest has the wrong slug.`);
    requireCondition(manifest.includes(`status: "${template.status}"`), `${template.slug} must be ${template.status}.`);
  }

  if (template.assets) {
    requireCondition(await exists(`docs/templates/${template.slug}/ASSETS.md`), `${template.slug} is ready but has no ASSETS.md.`);
    requireCondition(await exists(`public/templates/${template.slug}`), `${template.slug} is ready but has no public asset directory.`);
  }
}

requireCondition(await exists("docs/TEMPLATE_STANDARD.md"), "The template standard must live under docs/.");
requireCondition(await exists("docs/README.md"), "The documentation index is missing.");
requireCondition(templates.length === 6, "The approved portfolio must contain exactly six templates.");

if (failures.length) {
  console.error("ForgeBase template portfolio structure failed:\n");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log("ForgeBase template portfolio structure passed (6 templates checked)." );
