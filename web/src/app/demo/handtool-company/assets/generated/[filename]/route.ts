import { readFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";

const SVG_WIDTH = 1600;
const SVG_HEIGHT = 900;

type VisualSpec = {
  eyebrow: string;
  title: string;
  subtitle: string;
  accent: string;
  secondary: string;
  panel: string;
};

const MIME_BY_EXTENSION: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webp": "image/webp",
  ".svg": "image/svg+xml",
};

function escapeXml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&apos;");
}

function titleFromSlug(slug: string): string {
  return slug
    .split("-")
    .filter(Boolean)
    .map((token) => token.toUpperCase() === token ? token : token.charAt(0).toUpperCase() + token.slice(1))
    .join(" ");
}

function specForFilename(filename: string): VisualSpec {
  const baseName = filename.replace(path.extname(filename), "");

  if (baseName.startsWith("homepage-hero")) {
    return {
      eyebrow: "NorthForge Tools",
      title: "Taiwan OEM Hand Tool Manufacturing",
      subtitle: "Professional tool programs for brands, distributors, and industrial buyers.",
      accent: "#1d4ed8",
      secondary: "#0f172a",
      panel: "#dbeafe",
    };
  }

  if (baseName.startsWith("about-")) {
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

  if (baseName.startsWith("capability-")) {
    return {
      eyebrow: "Operational Capability",
      title: titleFromSlug(baseName.replace("capability-", "")),
      subtitle: "Workflow evidence that supports consistent product and packaging execution.",
      accent: "#7c3aed",
      secondary: "#3b0764",
      panel: "#ede9fe",
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

  return {
    eyebrow: "Demo Asset",
    title: titleFromSlug(baseName),
    subtitle: "Generated visual placeholder for content-aligned demo presentation.",
    accent: "#2563eb",
    secondary: "#1e293b",
    panel: "#e2e8f0",
  };
}

function buildSvg(spec: VisualSpec, filename: string): string {
  const eyebrow = escapeXml(spec.eyebrow);
  const title = escapeXml(spec.title);
  const subtitle = escapeXml(spec.subtitle);
  const fileLabel = escapeXml(filename);

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
  <rect x="120" y="142" width="156" height="34" rx="17" fill="${spec.accent}" fill-opacity="0.16" stroke="${spec.accent}" stroke-opacity="0.24" />
  <text x="198" y="164" text-anchor="middle" fill="${spec.accent}" font-family="Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="1.4">${eyebrow}</text>
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
  <text x="1010" y="214" fill="white" font-family="Arial, sans-serif" font-size="34" font-weight="700">NorthForge Demo Visual</text>
  <text x="1010" y="264" fill="white" fill-opacity="0.82" font-family="Arial, sans-serif" font-size="24">Content-aligned fallback for local preview and standalone verification.</text>
  <rect x="1010" y="342" width="380" height="244" rx="28" fill="white" fill-opacity="0.12" stroke="white" stroke-opacity="0.16" />
  <rect x="1050" y="384" width="240" height="22" rx="11" fill="white" fill-opacity="0.34" />
  <rect x="1050" y="430" width="296" height="22" rx="11" fill="white" fill-opacity="0.24" />
  <rect x="1050" y="476" width="264" height="22" rx="11" fill="white" fill-opacity="0.18" />
  <rect x="1050" y="536" width="116" height="116" rx="20" fill="white" fill-opacity="0.16" />
  <rect x="1192" y="536" width="116" height="116" rx="20" fill="white" fill-opacity="0.16" />
  <rect x="1334" y="536" width="116" height="116" rx="20" fill="white" fill-opacity="0.16" />
</svg>`;
}

async function readExistingAsset(filename: string): Promise<{ buffer: Buffer; contentType: string } | null> {
  const relativePath = path.join("demo", "handtool-company", "assets", "generated", filename);
  const candidates = [
    path.join(process.cwd(), "public", relativePath),
    path.join(process.cwd(), "..", "public", relativePath),
    path.join(process.cwd(), "..", "..", "public", relativePath),
    path.join(process.cwd(), relativePath),
    path.join(process.cwd(), "..", relativePath),
    path.join(process.cwd(), "..", "..", relativePath),
  ];

  for (const candidate of candidates) {
    try {
      const buffer = await readFile(candidate);
      const extension = path.extname(candidate).toLowerCase();
      return {
        buffer,
        contentType: MIME_BY_EXTENSION[extension] ?? "application/octet-stream",
      };
    } catch {
      // Try the next candidate path.
    }
  }

  return null;
}

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ filename: string }> },
) {
  const { filename } = await params;

  const existing = await readExistingAsset(filename);
  if (existing) {
    return new NextResponse(new Uint8Array(existing.buffer), {
      headers: {
        "Content-Type": existing.contentType,
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    });
  }

  const svg = buildSvg(specForFilename(filename), filename);

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}