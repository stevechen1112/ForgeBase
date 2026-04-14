import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCategoryBySlug, getProductsByCategory } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { ProductCard } from "@/components/ui/ProductCard";
import { FacetedFilterBar } from "@/components/ui/FacetedFilterBar";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getCategoryHeroImage } from "@/lib/demoAssets";
import { buildTwitterMeta } from "@/lib/seo";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

type Props = {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

/** 2.3.1 — any ?q= or ?page= param → noindex, canonical strips all params */
function isFaceted(filters: Record<string, string | string[] | undefined>): boolean {
  const SEO_PARAMS = new Set(["q", "page", "sort", "tag", "cert", "app"]);
  return Object.keys(filters).some((k) => SEO_PARAMS.has(k));
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { siteUrl: SITE_URL } = await getRuntimeSiteContext();
  const { categorySlug } = await params;
  const filters = await searchParams;
  const category = await getCategoryBySlug(categorySlug);
  if (!category) return { title: "Not Found" };

  const faceted = isFaceted(filters);

  const title = category.seo_title ?? category.category_name;
  const description = category.seo_description ?? category.description ?? undefined;
  const ogImage = category.og_image_url ?? category.image_url ?? undefined;

  return {
    title,
    description,
    // Canonical always points to the clean base URL — strips all filter/pagination params
    alternates: { canonical: `${SITE_URL}/products/${category.slug}` },
    openGraph: ogImage
      ? { images: [{ url: ogImage, width: 1200, height: 630, alt: title }] }
      : undefined,
    twitter: buildTwitterMeta({ title, description, imageUrl: ogImage ?? null }),
    // Faceted pages must not be indexed to avoid duplicate content (2.3.1)
    robots: faceted ? { index: false, follow: true } : undefined,
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { siteUrl: SITE_URL, siteConfig: runtimeSiteConfig } = await getRuntimeSiteContext();
  const { categorySlug } = await params;
  const filters = await searchParams;

  const category = await getCategoryBySlug(categorySlug);
  if (!category) notFound();

  const q = typeof filters.q === "string" ? filters.q : undefined;
  const page = typeof filters.page === "string" ? parseInt(filters.page, 10) || 1 : 1;

  const productRes = await getProductsByCategory(category.id, "en", page, 24, q);
  const products = productRes.data;
  const { total, total_pages } = productRes.meta;

  const faceted = isFaceted(filters);
  const baseUrl = `/products/${category.slug}`;
  const heroImage = getCategoryHeroImage(category.slug, category.image_url, runtimeSiteConfig);

  return (
    <>
      <PageViewTracker pageType="category" pageId={category.id} />
      <ChatWidget contextPage={baseUrl} contextEntityType="category" contextEntityId={category.id} />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Products", url: `${SITE_URL}/products` },
          { name: category.category_name, url: `${SITE_URL}/products/${category.slug}` },
        ])}
      />

      {/* Header */}
      <section className="relative overflow-hidden border-b border-gray-100 py-12 text-white">
        {heroImage && (
          <div
            className="absolute inset-0 bg-cover bg-center"
            style={{ backgroundImage: `url(${heroImage})` }}
          />
        )}
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/85 via-blue-950/78 to-blue-900/52" />
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="relative mb-3 text-xs text-blue-200/90">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/products" className="hover:underline">Products</Link>
            <span className="mx-1">/</span>
            <span className="text-white">{category.category_name}</span>
          </nav>
          <h1 className="relative text-3xl font-bold">{category.category_name}</h1>
          {category.description && (
            <p className="relative mt-2 max-w-2xl text-blue-100">{category.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
          )}
        </div>
      </section>

      {/* Product grid */}
      <section className="py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <div className="mb-8 grid gap-4 lg:grid-cols-3">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">Buyer Focus</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                Category pages are meant to help importers and distributors narrow down the right tool family before discussing SKU mix, packaging, and documentation.
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">Typical Questions</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                Buyers usually compare usage fit, target market, quality control expectation, and whether standard supply or customization is the better path.
              </p>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h2 className="text-sm font-semibold text-blue-900">Need a faster answer?</h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-800">
                If you already know your quantity, packaging need, or target market, move directly to RFQ and include the category context.
              </p>
            </div>
          </div>

          {/* Filter bar + noindex notice */}
          <div className="flex items-center justify-between mb-6 gap-4 flex-wrap">
            <FacetedFilterBar placeholder={`Search in ${category.category_name}…`} />
            <p className="text-sm text-gray-400">
              {total} product{total !== 1 ? "s" : ""}
              {q ? ` matching "${q}"` : ""}
            </p>
          </div>

          {/* noindex ribbon for faceted state */}
          {faceted && (
            <div className="mb-4 rounded-lg bg-yellow-50 border border-yellow-200 px-4 py-2 text-xs text-yellow-700">
              This filtered view is not indexed by search engines.{" "}
              <Link href={baseUrl} className="underline">View all products</Link>
            </div>
          )}

          {products.length === 0 ? (
            <p className="text-center text-gray-500 py-16">
              {q ? `No products found for "${q}".` : "No products in this category yet."}
            </p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {products.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  categorySlug={category.slug}
                  siteConfig={runtimeSiteConfig}
                />
              ))}
            </div>
          )}

          {/* Pagination — pages beyond 1 are noindex (handled in generateMetadata) */}
          {total_pages > 1 && (
            <nav className="mt-10 flex justify-center gap-2" aria-label="Pagination">
              {page > 1 && (
                <Link
                  href={page - 1 === 1 ? baseUrl : `${baseUrl}?page=${page - 1}${q ? `&q=${q}` : ""}`}
                  rel="prev"
                  className="px-4 py-2 rounded border text-sm hover:bg-gray-50"
                >
                  ← Prev
                </Link>
              )}
              <span className="px-4 py-2 text-sm text-gray-500">
                Page {page} / {total_pages}
              </span>
              {page < total_pages && (
                <Link
                  href={`${baseUrl}?page=${page + 1}${q ? `&q=${q}` : ""}`}
                  rel="next"
                  className="px-4 py-2 rounded border text-sm hover:bg-gray-50"
                >
                  Next →
                </Link>
              )}
            </nav>
          )}
        </div>
      </section>
    </>
  );
}
