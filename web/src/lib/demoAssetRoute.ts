import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

const SVG_WIDTH = 1600;
const SVG_HEIGHT = 900;
const CERT_BADGE_SIZE = 960;

export const MIME_BY_EXTENSION: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
  ".pdf": "application/pdf",
  ".ico": "image/x-icon",
};

type VisualSpec = {
  eyebrow: string;
  title: string;
  subtitle: string;
  accent: string;
  secondary: string;
  panel: string;
};

type CertificationBadgeVisual = {
  title: string;
  kicker: string;
  shortCode: string;
  accent: string;
  secondary: string;
  ring: string;
};

function escapeXml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function escapePdf(value: string): string {
  return value.replaceAll("\\", "\\\\").replaceAll("(", "\\(").replaceAll(")", "\\)");
}

function titleFromSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((token) =>
      token.toUpperCase() === token ? token : token.charAt(0).toUpperCase() + token.slice(1),
    )
    .join(" ");
}

function specForFilename(filename: string): VisualSpec {
  const baseName = filename.replace(path.extname(filename), "");

  if (baseName.startsWith("homepage-hero") || baseName.startsWith("page-home")) {
    return {
      eyebrow: "NorthForge Tools",
      title: "Taiwan OEM Hand Tool Manufacturing",
      subtitle: "Professional tool programs for brands, distributors, and industrial buyers.",
      accent: "#1d4ed8",
      secondary: "#0f172a",
      panel: "#dbeafe",
    };
  }

  if (baseName.startsWith("about-") || baseName.startsWith("page-about")) {
    return {
      eyebrow: "Factory Profile",
      title: "Process-Controlled Production Environment",
      subtitle: "Positioned for repeat orders, cleaner communication, and export-ready execution.",
      accent: "#0369a1",
      secondary: "#082f49",
      panel: "#e0f2fe",
    };
  }

  if (baseName.startsWith("category-")) {
    return {
      eyebrow: "Product Category",
      title: titleFromSlug(baseName.replace("category-", "").replace(/-hero$/, "")),
      subtitle: "Structured for B2B selection, comparison, and quote preparation.",
      accent: "#1d4ed8",
      secondary: "#172554",
      panel: "#eff6ff",
    };
  }

  if (baseName.startsWith("application-")) {
    return {
      eyebrow: "Industry Application",
      title: titleFromSlug(baseName.replace("application-", "")),
      subtitle: "Use-case framing for buyers matching tools, packaging, and program requirements.",
      accent: "#0f766e",
      secondary: "#134e4a",
      panel: "#ccfbf1",
    };
  }

  if (baseName.startsWith("capability-") || baseName.startsWith("icon-")) {
    return {
      eyebrow: baseName.startsWith("icon-") ? "Capability Icon" : "Operational Capability",
      title: titleFromSlug(baseName.replace("capability-", "").replace("icon-", "")),
      subtitle: "Workflow evidence that supports consistent product and packaging execution.",
      accent: "#7c3aed",
      secondary: "#3b0764",
      panel: "#ede9fe",
    };
  }

  if (baseName.startsWith("cert-") || baseName.startsWith("pdf-")) {
    return {
      eyebrow: baseName.startsWith("pdf-") ? "Compliance Document" : "Certification Badge",
      title: titleFromSlug(baseName.replace("cert-", "").replace("pdf-", "").replace(/-badge$/, "")),
      subtitle: "Demo compliance asset placeholder for certification and documentation flows.",
      accent: "#0f766e",
      secondary: "#134e4a",
      panel: "#dcfce7",
    };
  }

  if (baseName.startsWith("product-")) {
    const model = baseName.replace("product-", "").replace(/-main$/, "").toUpperCase();
    return {
      eyebrow: "Product Visual",
      title: model,
      subtitle: "Demo rendering for product-card, detail-page, and related-program presentation.",
      accent: "#ea580c",
      secondary: "#7c2d12",
      panel: "#ffedd5",
    };
  }

  if (baseName.startsWith("logo-")) {
    return {
      eyebrow: "NorthForge Tools",
      title: "Brand Asset",
      subtitle: titleFromSlug(baseName.replace("logo-", "")),
      accent: "#1d4ed8",
      secondary: "#0f172a",
      panel: "#dbeafe",
    };
  }

  return {
    eyebrow: "Demo Asset",
    title: titleFromSlug(baseName),
    subtitle: "Generated fallback for content-aligned demo presentation.",
    accent: "#2563eb",
    secondary: "#1e293b",
    panel: "#e2e8f0",
  };
}

function splitTitle(title: string, maxLineLength = 16): string[] {
  const words = title.split(" ");
  const lines: string[] = [];
  let currentLine = "";

  for (const word of words) {
    const next = currentLine ? `${currentLine} ${word}` : word;
    if (next.length > maxLineLength && currentLine) {
      lines.push(currentLine);
      currentLine = word;
    } else {
      currentLine = next;
    }
  }

  if (currentLine) {
    lines.push(currentLine);
  }

  return lines.slice(0, 3);
}

function certificationBadgeSpec(filename: string): CertificationBadgeVisual {
  const baseName = filename.replace(path.extname(filename), "");

  if (baseName.includes("iso-9001")) {
    return {
      title: "ISO 9001",
      kicker: "Quality Management",
      shortCode: "QMS",
      accent: "#0f766e",
      secondary: "#134e4a",
      ring: "#99f6e4",
    };
  }

  if (baseName.includes("vde")) {
    return {
      title: "VDE Workflow",
      kicker: "Insulated Tools",
      shortCode: "VDE",
      accent: "#2563eb",
      secondary: "#1e3a8a",
      ring: "#bfdbfe",
    };
  }

  if (baseName.includes("rohs")) {
    return {
      title: "RoHS",
      kicker: "Material Compliance",
      shortCode: "RoHS",
      accent: "#16a34a",
      secondary: "#166534",
      ring: "#bbf7d0",
    };
  }

  if (baseName.includes("reach")) {
    return {
      title: "REACH",
      kicker: "Documentation",
      shortCode: "REACH",
      accent: "#7c3aed",
      secondary: "#581c87",
      ring: "#ddd6fe",
    };
  }

  if (baseName.includes("pre-shipment-inspection")) {
    return {
      title: "Pre-Shipment",
      kicker: "Inspection Support",
      shortCode: "PSI",
      accent: "#ea580c",
      secondary: "#9a3412",
      ring: "#fed7aa",
    };
  }

  return {
    title: titleFromSlug(baseName.replace("cert-", "").replace(/-badge$/, "")),
    kicker: "NorthForge Certification",
    shortCode: "NF",
    accent: "#0f766e",
    secondary: "#134e4a",
    ring: "#ccfbf1",
  };
}

function buildCertificationBadgeSvg(filename: string, label: string): string {
  const spec = certificationBadgeSpec(filename);
  const titleLines = splitTitle(spec.title, 14).map(escapeXml);
  const kicker = escapeXml(spec.kicker);
  const shortCode = escapeXml(spec.shortCode);
  const fileLabel = escapeXml(label);

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${CERT_BADGE_SIZE}" height="${CERT_BADGE_SIZE}" viewBox="0 0 ${CERT_BADGE_SIZE} ${CERT_BADGE_SIZE}" role="img" aria-label="${escapeXml(spec.title)}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ffffff" />
      <stop offset="100%" stop-color="#f8fafc" />
    </linearGradient>
    <linearGradient id="panel" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="${spec.ring}" stop-opacity="0.9" />
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0.98" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" rx="112" fill="url(#bg)" />
  <circle cx="480" cy="480" r="358" fill="${spec.secondary}" />
  <circle cx="480" cy="480" r="316" fill="url(#panel)" stroke="${spec.ring}" stroke-width="20" />
  <circle cx="480" cy="480" r="246" fill="#ffffff" stroke="${spec.accent}" stroke-opacity="0.18" stroke-width="12" />
  <circle cx="480" cy="262" r="58" fill="${spec.accent}" fill-opacity="0.12" />
  <text x="480" y="280" text-anchor="middle" fill="${spec.accent}" font-family="Arial, sans-serif" font-size="46" font-weight="800" letter-spacing="3">${shortCode}</text>
  <text x="480" y="390" text-anchor="middle" fill="#0f172a" font-family="Arial, sans-serif" font-size="66" font-weight="800">${titleLines[0] ?? ""}</text>
  ${titleLines[1] ? `<text x="480" y="458" text-anchor="middle" fill="#0f172a" font-family="Arial, sans-serif" font-size="66" font-weight="800">${titleLines[1]}</text>` : ""}
  ${titleLines[2] ? `<text x="480" y="526" text-anchor="middle" fill="#0f172a" font-family="Arial, sans-serif" font-size="58" font-weight="800">${titleLines[2]}</text>` : ""}
  <rect x="218" y="590" width="524" height="78" rx="39" fill="${spec.accent}" fill-opacity="0.1" />
  <text x="480" y="638" text-anchor="middle" fill="${spec.secondary}" font-family="Arial, sans-serif" font-size="34" font-weight="700" letter-spacing="1.2">${kicker}</text>
  <text x="480" y="724" text-anchor="middle" fill="#64748b" font-family="Arial, sans-serif" font-size="24">NorthForge Demo Certification Badge</text>
  <text x="480" y="768" text-anchor="middle" fill="#94a3b8" font-family="Arial, sans-serif" font-size="18">${fileLabel}</text>
</svg>`;
}

function buildSvg(spec: VisualSpec, label: string): string {
  const eyebrow = escapeXml(spec.eyebrow);
  const title = escapeXml(spec.title);
  const subtitle = escapeXml(spec.subtitle);
  const fileLabel = escapeXml(label);

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${SVG_WIDTH}" height="${SVG_HEIGHT}" viewBox="0 0 ${SVG_WIDTH} ${SVG_HEIGHT}" role="img" aria-label="${title}">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="${spec.secondary}" />
      <stop offset="100%" stop-color="${spec.accent}" />
    </linearGradient>
    <linearGradient id="panel" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" stop-color="white" stop-opacity="0.92" />
      <stop offset="100%" stop-color="${spec.panel}" stop-opacity="0.92" />
    </linearGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg)" />
  <circle cx="1290" cy="160" r="210" fill="white" fill-opacity="0.08" />
  <circle cx="1410" cy="740" r="240" fill="white" fill-opacity="0.08" />
  <rect x="84" y="96" width="760" height="708" rx="36" fill="url(#panel)" />
  <rect x="120" y="142" width="176" height="34" rx="17" fill="${spec.accent}" fill-opacity="0.16" stroke="${spec.accent}" stroke-opacity="0.24" />
  <text x="208" y="164" text-anchor="middle" fill="${spec.accent}" font-family="Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="1.2">${eyebrow}</text>
  <text x="120" y="278" fill="#0f172a" font-family="Arial, sans-serif" font-size="64" font-weight="800">${title}</text>
  <text x="120" y="338" fill="#334155" font-family="Arial, sans-serif" font-size="28">${subtitle}</text>
  <rect x="120" y="410" width="428" height="220" rx="28" fill="white" fill-opacity="0.84" />
  <rect x="576" y="410" width="212" height="220" rx="28" fill="${spec.accent}" fill-opacity="0.12" />
  <rect x="616" y="452" width="132" height="18" rx="9" fill="${spec.accent}" fill-opacity="0.28" />
  <rect x="616" y="494" width="96" height="18" rx="9" fill="${spec.accent}" fill-opacity="0.22" />
  <rect x="616" y="536" width="112" height="18" rx="9" fill="${spec.accent}" fill-opacity="0.16" />
  <path d="M168 560 C250 430, 354 430, 450 560" fill="none" stroke="${spec.accent}" stroke-width="24" stroke-linecap="round" />
  <path d="M210 580 L286 472 L356 542 L446 446" fill="none" stroke="${spec.secondary}" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" />
  <circle cx="446" cy="446" r="18" fill="${spec.accent}" />
  <rect x="120" y="672" width="668" height="68" rx="18" fill="#0f172a" fill-opacity="0.06" />
  <text x="152" y="715" fill="#475569" font-family="Arial, sans-serif" font-size="20">${fileLabel}</text>
  <text x="1010" y="214" fill="white" font-family="Arial, sans-serif" font-size="34" font-weight="700">NorthForge Demo Asset</text>
  <text x="1010" y="264" fill="white" fill-opacity="0.82" font-family="Arial, sans-serif" font-size="24">Served directly from repo source or generated fallback.</text>
</svg>`;
}

function buildPdfBuffer(filename: string): Buffer {
  const spec = specForFilename(filename);
  const lines = [
    "NorthForge Demo Document",
    spec.title,
    spec.subtitle,
    `Source: ${filename}`,
  ];
  const content = [
    "BT",
    "/F1 24 Tf",
    "72 720 Td",
    `(${escapePdf(lines[0])}) Tj`,
    "0 -36 Td",
    "/F1 18 Tf",
    `(${escapePdf(lines[1])}) Tj`,
    "0 -28 Td",
    "/F1 12 Tf",
    `(${escapePdf(lines[2])}) Tj`,
    "0 -22 Td",
    `(${escapePdf(lines[3])}) Tj`,
    "ET",
  ].join("\n");

  const objects = [
    "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
    "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
    "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
    "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    `5 0 obj\n<< /Length ${Buffer.byteLength(content, "utf8")} >>\nstream\n${content}\nendstream\nendobj\n`,
  ];

  let pdf = "%PDF-1.4\n";
  const offsets = [0];
  for (const object of objects) {
    offsets.push(Buffer.byteLength(pdf, "utf8"));
    pdf += object;
  }

  const xrefStart = Buffer.byteLength(pdf, "utf8");
  pdf += `xref\n0 ${objects.length + 1}\n`;
  pdf += "0000000000 65535 f \n";
  for (let index = 1; index <= objects.length; index += 1) {
    pdf += `${String(offsets[index]).padStart(10, "0")} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return Buffer.from(pdf, "utf8");
}

function getAssetRootCandidates(): string[] {
  const cwd = process.cwd();
  return [
    path.join(cwd, "demo", "handtool-company", "assets"),
    path.join(cwd, "..", "demo", "handtool-company", "assets"),
    path.join(cwd, "..", "..", "demo", "handtool-company", "assets"),
    path.join(cwd, "..", "..", "..", "demo", "handtool-company", "assets"),
    path.join(cwd, "..", "..", "..", "..", "demo", "handtool-company", "assets"),
  ];
}

export async function readDemoAsset(assetSegments: string[]) {
  const safeSegments = assetSegments.filter(Boolean);
  if (safeSegments.some((segment) => segment === "." || segment === ".." || segment.includes(".."))) {
    return null;
  }

  for (const root of getAssetRootCandidates()) {
    const candidate = path.join(root, ...safeSegments);
    try {
      const buffer = await readFile(candidate);
      const extension = path.extname(candidate).toLowerCase();
      return {
        buffer,
        contentType: MIME_BY_EXTENSION[extension] ?? "application/octet-stream",
      };
    } catch {
      // Keep searching other candidate roots.
    }
  }

  return null;
}

export async function createDemoAssetResponse(assetSegments: string[]) {
  const existing = await readDemoAsset(assetSegments);
  if (existing) {
    return new NextResponse(new Uint8Array(existing.buffer), {
      headers: {
        "Content-Type": existing.contentType,
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    });
  }

  const filename = assetSegments[assetSegments.length - 1] ?? "demo-asset";
  const extension = path.extname(filename).toLowerCase();

  if (extension === ".pdf") {
    return new NextResponse(new Uint8Array(buildPdfBuffer(filename)), {
      headers: {
        "Content-Type": "application/pdf",
        "Cache-Control": "public, max-age=3600",
        "Content-Disposition": `inline; filename="${filename}"`,
      },
    });
  }

  if (filename.startsWith("cert-") && filename.includes("-badge")) {
    return new NextResponse(buildCertificationBadgeSvg(filename, assetSegments.join("/")), {
      headers: {
        "Content-Type": "image/svg+xml; charset=utf-8",
        "Cache-Control": "public, max-age=3600",
      },
    });
  }

  const svg = buildSvg(specForFilename(filename), assetSegments.join("/"));
  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}

export function createFaviconSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="NorthForge Tools">
  <rect width="64" height="64" rx="14" fill="#0f172a"/>
  <rect x="10" y="10" width="44" height="44" rx="10" fill="#1d4ed8"/>
  <path d="M20 44V20h6l12 15V20h6v24h-6L26 29v15z" fill="white"/>
</svg>`;
}
