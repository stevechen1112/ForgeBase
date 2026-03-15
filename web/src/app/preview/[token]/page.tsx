/**
 * 1a.6.4 內容預覽頁面
 *
 * Validates a short-lived preview token from the admin and renders the
 * page content regardless of its publication status.  Displays a visible
 * "PREVIEW MODE" banner so editors know they are looking at a draft.
 *
 * Route: /preview/[token]
 */
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

type Props = { params: Promise<{ token: string }> };

const BASE =
  process.env.API_INTERNAL_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

interface PagePreview {
  id: string;
  slug: string;
  page_type: string;
  title: string;
  subtitle?: string;
  body?: string;
  hero_image_url?: string;
  seo_title?: string;
  seo_description?: string;
  locale: string;
  status: string;
}

async function fetchPreviewPage(token: string): Promise<PagePreview | null> {
  try {
    const res = await fetch(`${BASE}/api/v1/content/preview/${token}`, {
      cache: "no-store", // always fresh — never cache previews
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params;
  const page = await fetchPreviewPage(token);
  if (!page) return { title: "Preview Not Found" };
  return {
    title: `[PREVIEW] ${page.seo_title ?? page.title}`,
    description: page.seo_description,
    robots: { index: false, follow: false }, // never index preview pages
  };
}

export default async function PreviewPage({ params }: Props) {
  const { token } = await params;
  const page = await fetchPreviewPage(token);

  if (!page) {
    notFound();
  }

  // Parse body blocks if JSON; otherwise treat as plain text / HTML
  let bodyContent: string | null = page.body ?? null;
  if (bodyContent) {
    try {
      const parsed = JSON.parse(bodyContent);
      // If it's an array of block objects, extract text fields for display
      if (Array.isArray(parsed)) {
        bodyContent = parsed
          .map((block: { text?: string; content?: string; value?: string }) =>
            block.text ?? block.content ?? block.value ?? ""
          )
          .filter(Boolean)
          .join("\n\n");
      }
    } catch {
      // Not JSON — use as-is (plain text or HTML string)
    }
  }

  return (
    <>
      {/* ── Preview banner ── */}
      <div className="sticky top-0 z-50 flex items-center justify-between bg-amber-400 px-4 py-2 text-sm font-semibold text-amber-900 shadow">
        <div className="flex items-center gap-2">
          <span className="rounded bg-amber-700 px-2 py-0.5 text-xs text-white">
            PREVIEW
          </span>
          <span>
            You are previewing a <strong>{page.status}</strong> page — this URL
            expires in 1 hour.
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="font-mono opacity-70">/{page.slug}</span>
          <Link
            href="/"
            className="rounded border border-amber-700 px-3 py-1 hover:bg-amber-500 transition-colors"
          >
            ← Exit Preview
          </Link>
        </div>
      </div>

      {/* ── Hero ── */}
      <section
        className="relative overflow-hidden bg-gradient-to-br from-slate-800 to-slate-600 py-20 text-white"
        style={
          page.hero_image_url
            ? {
                backgroundImage: `url(${page.hero_image_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : undefined
        }
      >
        {page.hero_image_url && (
          <div className="absolute inset-0 bg-slate-900/65" aria-hidden="true" />
        )}
        <div className="relative container mx-auto max-w-4xl px-6 text-center">
          <span className="mb-3 inline-block rounded-full border border-white/30 px-3 py-0.5 text-xs uppercase tracking-widest text-white/70">
            {page.page_type}
          </span>
          <h1 className="text-4xl font-bold sm:text-5xl">{page.title}</h1>
          {page.subtitle && (
            <p className="mt-4 text-xl text-slate-200">{page.subtitle}</p>
          )}
        </div>
      </section>

      {/* ── Body ── */}
      {bodyContent && (
        <section className="py-14">
          <div className="container mx-auto max-w-4xl px-6">
            <div className="prose prose-gray max-w-none text-gray-700 leading-relaxed whitespace-pre-line">
              {bodyContent}
            </div>
          </div>
        </section>
      )}

      {/* ── Meta info (visible in preview only) ── */}
      <section className="border-t bg-gray-50 py-8">
        <div className="container mx-auto max-w-4xl px-6">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-widest text-gray-400">
            Preview Metadata
          </h2>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            {[
              ["Page ID", page.id],
              ["Slug", page.slug],
              ["Type", page.page_type],
              ["Locale", page.locale],
              ["Status", page.status],
              ["SEO Title", page.seo_title ?? "—"],
              ["SEO Description", page.seo_description ?? "—"],
            ].map(([label, value]) => (
              <div key={label} className="flex gap-2">
                <dt className="w-36 shrink-0 font-medium text-gray-500">{label}</dt>
                <dd className="text-gray-700 break-all">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>
    </>
  );
}
