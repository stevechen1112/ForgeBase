import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCategoryBySlug, getProductsByCategory } from "@/lib/api";
import { ProductCard } from "@/components/ui/ProductCard";
import { FacetedFilterBar } from "@/components/ui/FacetedFilterBar";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getCategoryHeroImage } from "@/lib/demoAssets";

type Props = {
  params: Promise<{ categorySlug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

/** 2.3.1 — any ?q= or ?page= param → noindex, canonical strips all params */
function isFaceted(filters: Record<string, string | string[] | undefined>): boolean {
  const SEO_PARAMS = new Set(["q", "page", "sort", "tag", "cert", "app"]);
  return Object.keys(filters).some((k) => SEO_PARAMS.has(k));
}

export async function generateMetadata({ params, searchParams }: Props): Promise<Metadata> {
  const { categorySlug } = await params;
  const filters = await searchParams;
  const category = await getCategoryBySlug(categorySlug);
  if (!category) return { title: "Not Found" };

  const faceted = isFaceted(filters);

  return {
    title: category.seo_title ?? category.category_name,
    description: category.seo_description ?? category.description ?? undefined,
    // Canonical always points to the clean base URL — strips all filter/pagination params
    alternates: { canonical: `${SITE_URL}/products/${category.slug}` },
    // Faceted pages must not be indexed to avoid duplicate content (2.3.1)
    robots: faceted ? { index: false, follow: true } : undefined,
  };
}

export default async function CategoryPage({ params, searchParams }: Props) {
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
  const heroImage = getCategoryHeroImage(category.slug, category.image_url);

  return (
    <>
      <PageViewTracker pageType="category" pageId={category.id} />
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
