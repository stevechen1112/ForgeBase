import { Link } from "@/i18n/navigation";
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
import { ChatWidget } from "@/components/chat/ChatWidget";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { CUSTOM_PACKAGING_IMAGE, QUALITY_INSPECTION_IMAGE, getProductImage } from "@/lib/demoAssets";
import { buildCanonicalUrl, buildLocaleAlternates, getSiteUrl } from "@/lib/seo";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";

type Props = { params: Promise<{ locale: string; categorySlug: string; productSlug: string }> };

const SITE_URL = getSiteUrl();
const BRAND_NAME = process.env.NEXT_PUBLIC_SITE_NAME === "ForgeBase"
  ? "NorthForge Tools"
  : (process.env.NEXT_PUBLIC_SITE_NAME || "NorthForge Tools");

type CommonMessages = {
  home: string;
};

type ProductDetailMessages = {
  products: string;
  introBox: string;
  overview: string;
  inspectionTitle: string;
  inspectionDescription: string;
  packagingTitle: string;
  packagingDescription: string;
  readinessTitle: string;
  readinessDescription: string;
  specControlTitle: string;
  specControlDescription: string;
  contextTitle: string;
  contextDescription: string;
  specsTitle: string;
  faqTitle: string;
  appTitle: string;
  appLearnMore: string;
  certTitle: string;
  beforeRfqTitle: string;
  beforeRfqDescription: string;
  rfqItems: Array<{ label: string; detail: string }>;
  submitRfq: string;
  askFirst: string;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, categorySlug, productSlug } = await params;
  const product = await getProductBySlug(productSlug, locale);
  if (!product) return { title: "Not Found" };

  const pagePath = `/products/${categorySlug}/${product.slug}`;
  const canonical = buildCanonicalUrl(pagePath);

  // hreflang: fetch all published locale variants of this slug
  const localeVariants = await getProductLocales(product.slug).catch(() => []);
  const languages = buildLocaleAlternates(pagePath, localeVariants);

  return {
    title: product.seo_title ?? `${product.model_number} ${product.product_name}`,
    description: product.seo_description ?? product.short_description,
    alternates: {
      canonical,
      languages,
    },
  };
}

export default async function ProductDetailPage({ params }: Props) {
  const { locale, categorySlug, productSlug } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<ProductDetailMessages>("productDetail"),
  ]);

  const [product, category] = await Promise.all([
    getProductBySlug(productSlug, locale),
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
  const faqs = await getPublishedFAQs(locale, category.slug);

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
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [product, category, ...faqs, ...relatedApps, ...relatedCerts, ...extraFaqs]);

  const productUrl = `${SITE_URL}/products/${category.slug}/${product.slug}`;
  const productImage = getProductImage(product, category.slug);
  const specMap = specs?.length
    ? Object.fromEntries(specs.map((spec) => [spec.name, spec.value]))
    : undefined;

  return (
    <>
      <PageViewTracker pageType="product" pageId={product.id} />
      <ChatWidget
        contextPage={`/products/${category.slug}/${product.slug}`}
        contextEntityType="product"
        contextEntityId={product.id}
      />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.products, url: `${SITE_URL}/products` },
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
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/products" className="hover:underline">{copy.products}</Link>
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
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
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
              <div className="mt-5 rounded-xl border border-blue-100 bg-blue-50 p-4">
                <p className="text-sm leading-relaxed text-blue-900">
                  {copy.introBox}
                </p>
              </div>

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
              <h2 className="text-xl font-semibold text-gray-800 mb-4">{copy.overview}</h2>
              <div
                className="prose prose-gray max-w-none text-gray-600 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: product.full_description }}
              />
            </div>
          )}

          <div className="mt-12 grid gap-6 lg:grid-cols-2">
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={QUALITY_INSPECTION_IMAGE}
                alt="NorthForge quality inspection workflow"
                className="h-56 w-full object-cover"
              />
              <div className="p-5">
                <h2 className="text-base font-semibold text-gray-900">{copy.inspectionTitle}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">
                  {copy.inspectionDescription}
                </p>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={CUSTOM_PACKAGING_IMAGE}
                alt="NorthForge private-label packaging support"
                className="h-56 w-full object-cover"
              />
              <div className="p-5">
                <h2 className="text-base font-semibold text-gray-900">{copy.packagingTitle}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">
                  {copy.packagingDescription}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-12 grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">{copy.readinessTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                {copy.readinessDescription}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">{copy.specControlTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                {copy.specControlDescription}
              </p>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">{copy.contextTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                {copy.contextDescription}
              </p>
            </div>
          </div>

          {/* Specifications table */}
          {specs && specs.length > 0 && (
            <div className="mt-12">
              <h2 className="text-xl font-semibold text-gray-800 mb-4">{copy.specsTitle}</h2>
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
                {copy.faqTitle}
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
                {copy.appTitle}
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
                      {copy.appLearnMore}
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
                {copy.certTitle}
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

      {/* Pre-RFQ Advisory & CTA */}
      <section className="bg-blue-50 border-t border-blue-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <h2 className="text-xl font-semibold text-gray-900">{copy.beforeRfqTitle}</h2>
          <p className="mt-2 max-w-2xl text-sm text-gray-600">
            {copy.beforeRfqDescription}
          </p>
          <ul className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {copy.rfqItems.map((item) => (
              <li key={item.label} className="flex gap-3 rounded-xl border border-blue-100 bg-white p-4 shadow-sm">
                <svg className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4" />
                </svg>
                <div>
                  <p className="text-sm font-semibold text-gray-800">{item.label}</p>
                  <p className="mt-0.5 text-xs leading-relaxed text-gray-500">{item.detail}</p>
                </div>
              </li>
            ))}
          </ul>
          <div className="mt-8 flex flex-wrap gap-4">
            <Link
              href={`/rfq?product=${encodeURIComponent(product.model_number ?? product.product_name)}`}
              className="rounded-lg bg-blue-700 px-7 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              {copy.submitRfq}
            </Link>
            <Link
              href="/contact"
              className="rounded-lg border border-gray-300 bg-white px-7 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copy.askFirst}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
