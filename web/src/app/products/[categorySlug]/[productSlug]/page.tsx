import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  getCategoryBySlug,
  getProductBySlug,
  getPublishedFAQs,
  getProductRelatedApplications,
  getProductRelatedCertifications,
  getProductRelatedFAQs,
  getProductAlternatives,
  getProductIndexedDocs,
  getProductLocales,
} from "@/lib/api";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import {
  StructuredData,
  buildBreadcrumbSchema,
  buildProductSchema,
  buildFAQSchema,
} from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { ProductCTAButtons } from "@/components/ui/ProductCTAButtons";
import { DownloadGateModal } from "@/components/ui/DownloadGateModal";
import { getProductImage } from "@/lib/demoAssets";

type Props = { params: Promise<{ categorySlug: string; productSlug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
const BRAND_NAME = process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { categorySlug, productSlug } = await params;
  const product = await getProductBySlug(productSlug);
  if (!product) return { title: "Not Found" };

  const canonical = `${SITE_URL}/products/${categorySlug}/${product.slug}`;

  // hreflang: fetch all published locale variants of this slug
  const localeVariants = await getProductLocales(product.slug).catch(() => []);
  const languages: Record<string, string> = { "x-default": canonical };
  for (const v of localeVariants) {
    const url =
      v.locale === "en"
        ? `${SITE_URL}/products/${categorySlug}/${product.slug}`
        : `${SITE_URL}/${v.locale}/products/${categorySlug}/${product.slug}`;
    languages[v.locale] = url;
  }
  if (!("en" in languages)) languages.en = canonical;

  return {
    title: product.seo_title ?? `${product.model_number} ${product.product_name}`,
    description: product.seo_description ?? product.short_description,
    alternates: {
      canonical,
      languages: Object.keys(languages).length > 2 ? languages : undefined,
    },
  };
}

export default async function ProductDetailPage({ params }: Props) {
  const { categorySlug, productSlug } = await params;

  const [product, category] = await Promise.all([
    getProductBySlug(productSlug),
    getCategoryBySlug(categorySlug),
  ]);

  if (!product || !category) notFound();

  // Parse specifications JSON (if any)
  // Seed data uses [{name, value}] array format
  type SpecRow = { name: string; value: string };
  let specs: SpecRow[] | null = null;
  if (product.specifications) {
    try {
      const parsed = JSON.parse(product.specifications);
      if (Array.isArray(parsed)) {
        specs = parsed as SpecRow[];
      } else if (parsed && typeof parsed === "object") {
        specs = Object.entries(parsed).map(([name, value]) => ({ name, value: String(value) }));
      }
    } catch {
      // ignore malformed specs
    }
  }

  // Fetch FAQs tagged to this product's category
  const faqs = await getPublishedFAQs("en", category.slug);

  // Fetch M2M linked data in parallel (1a.5.12 内連自動化)
  const [relatedApps, relatedCerts, linkedFaqs, alternatives, indexedDocs] = await Promise.all([
    getProductRelatedApplications(product.id).catch(() => []),
    getProductRelatedCertifications(product.id).catch(() => []),
    getProductRelatedFAQs(product.id).catch(() => []),
    getProductAlternatives(product.id).catch(() => []),
    getProductIndexedDocs(product.id).catch(() => []),
  ]);

  // Merge linked FAQs (deduplicated by question)
  const allFaqQuestions = new Set(faqs.map((f) => f.question));
  const extraFaqs = linkedFaqs.filter((f) => !allFaqQuestions.has(f.question));

  const productUrl = `${SITE_URL}/products/${category.slug}/${product.slug}`;
  const productImage = getProductImage(product, category.slug);
  const specMap = specs?.length
    ? Object.fromEntries(specs.map((spec) => [spec.name, spec.value]))
    : undefined;

  return (
    <>
      <PageViewTracker pageType="product" pageId={product.id} />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Products", url: `${SITE_URL}/products` },
          { name: category.category_name, url: `${SITE_URL}/products/${category.slug}` },
          { name: product.product_name, url: productUrl },
        ])}
      />
      <StructuredData
        data={buildProductSchema({
          name: product.product_name,
          description: product.short_description,
          model: product.model_number,
          brand: BRAND_NAME,
          url: productUrl,
          siteUrl: SITE_URL,
          specs: specMap,
          certifications: relatedCerts,
          alternatives: alternatives.map((a) => ({
            product_name: a.product_name,
            model_number: a.model_number,
            slug: a.slug,
            // No categorySlug available in PublicRelatedProduct — URL omitted
          })),
        })}
      />
      {faqs.length > 0 && (
        <StructuredData
          data={buildFAQSchema(faqs.map((f) => ({ question: f.question, answer: f.answer })))}
        />
      )}

      {/* Breadcrumb */}
      <div className="bg-gray-50 border-b border-gray-100 py-4">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/products" className="hover:underline">Products</Link>
            <span className="mx-1">/</span>
            <Link href={`/products/${category.slug}`} className="hover:underline">
              {category.category_name}
            </Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{product.product_name}</span>
          </nav>
        </div>
      </div>

      {/* Main content */}
      <section className="py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <div className="grid gap-10 lg:grid-cols-2">
            {/* Left: image placeholder */}
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-gray-100 aspect-square max-h-96 lg:max-h-full">
              {productImage ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={productImage}
                  alt={product.product_name}
                  className="h-full w-full object-cover"
                />
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-24 w-24 text-gray-300"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1}
                    d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                  />
                </svg>
              )}
            </div>

            {/* Right: info */}
            <div>
              <p className="text-sm font-mono text-gray-400">{product.model_number}</p>
              <h1 className="mt-1 text-3xl font-bold text-gray-800">{product.product_name}</h1>
              <p className="mt-4 text-gray-600 leading-relaxed">{product.short_description}</p>

              {/* CTA */}
              <ProductCTAButtons
                productId={product.id}
                productName={product.product_name}
                categorySlug={category.slug}
                categoryName={category.category_name}
              />
              {/* Download Gate (2.1.5) */}
              <DownloadGateModal
                productId={product.id}
                productName={product.product_name}
                docs={indexedDocs}
              />
            </div>
          </div>

          {/* Full description */}
          {product.full_description && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Product Overview</h2>
              <div
                className="prose prose-gray max-w-none text-gray-600 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: product.full_description }}
              />
            </div>
          )}

          {/* Specifications table */}
          {specs && specs.length > 0 && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">Specifications</h2>
              <div className="overflow-hidden rounded-xl border border-gray-200">
                <table className="w-full text-sm">
                  <tbody className="divide-y divide-gray-100">
                    {specs.map((spec, i) => (
                      <tr key={i} className="bg-white even:bg-gray-50">
                        <td className="py-3 px-5 font-medium text-gray-700 w-1/3">{spec.name}</td>
                        <td className="py-3 px-5 text-gray-600">{spec.value}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* FAQs — category-tagged + product-linked */}
          {(faqs.length > 0 || extraFaqs.length > 0) && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Frequently Asked Questions
              </h2>
              <FAQAccordion
                items={[
                  ...faqs,
                  ...extraFaqs.map((f) => ({
                    id: f.id,
                    question: f.question,
                    answer: f.answer,
                    locale: f.locale ?? "en",
                    status: "published" as const,
                    sort_order: 0,
                    category_tag: null,
                    seo_title: null,
                    seo_description: null,
                    slug: f.id,
                    created_at: "",
                    updated_at: "",
                  })),
                ]}
              />
            </div>
          )}

          {/* Related Applications (M2M) */}
          {relatedApps.length > 0 && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Application Scenarios
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {relatedApps.map((app) => (
                  <Link
                    key={app.id}
                    href={`/applications/${app.slug}`}
                    className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all"
                  >
                    {app.industry && (
                      <span className="text-xs font-medium text-blue-600 uppercase tracking-wide">
                        {app.industry}
                      </span>
                    )}
                    <h3 className="mt-1 font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                      {app.application_name}
                    </h3>
                    {app.description && (
                      <p className="mt-2 text-sm text-gray-500 line-clamp-2">{app.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
                    )}
                    <span className="mt-3 inline-block text-xs text-blue-600 group-hover:underline">
                      Learn more →
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Certifications (M2M) */}
          {relatedCerts.length > 0 && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">
                Certifications &amp; Compliance
              </h2>
              <div className="flex flex-wrap gap-3">
                {relatedCerts.map((cert) => (
                  <div
                    key={cert.id}
                    className="flex items-center gap-2 rounded-full border border-green-200 bg-green-50 px-4 py-2"
                    title={cert.description ?? cert.cert_name}
                  >
                    {cert.badge_icon_url ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={cert.badge_icon_url}
                        alt={cert.cert_name}
                        className="h-5 w-5 object-contain"
                      />
                    ) : (
                      <svg
                        className="h-4 w-4 text-green-600"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
                        />
                      </svg>
                    )}
                    <span className="text-sm font-medium text-green-800">{cert.cert_name}</span>
                    {cert.issuing_body && (
                      <span className="text-xs text-green-600">({cert.issuing_body})</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </>
  );
}
