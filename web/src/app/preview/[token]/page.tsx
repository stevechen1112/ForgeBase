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
import { FlexiblePageRenderer } from "@/components/pages/FlexiblePageRenderer";
import { withRequestTenantHeaders } from "@/lib/serverTenant";

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
  subtitle: string | null;
  body: string | null;
  hero_image_url: string | null;
  seo_title: string | null;
  seo_description: string | null;
  og_image_url: string | null;
  canonical_url: string | null;
  structured_data: string | null;
  noindex: boolean;
  entity_type: string | null;
  entity_id: string | null;
  locale: string;
  status: string;
}

async function fetchPreviewPage(token: string): Promise<PagePreview | null> {
  try {
    const tenantRequest = await withRequestTenantHeaders();
    const res = await fetch(`${BASE}/api/v1/content/preview/${token}`, {
      headers: tenantRequest.headers,
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

      <FlexiblePageRenderer page={page} />

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
