import { Link } from "@/i18n/navigation";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  getApplicationBySlug,
  getApplicationRelatedProducts,
  getApplicationRelatedFAQs,
  getApplicationLocales,
} from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { buildCanonicalUrl, buildLocaleAlternates, buildTwitterMeta, getSiteUrl } from "@/lib/seo";
import { CUSTOM_PACKAGING_IMAGE, QUALITY_INSPECTION_IMAGE, getApplicationImage, getProductImage } from "@/lib/demoAssets";
import { siteConfig } from "@/lib/siteConfig";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";

type Props = { params: Promise<{ locale: string; applicationSlug: string }> };

const SITE_URL = getSiteUrl();

type CommonMessages = {
  home: string;
};

type ApplicationDetailMessages = {
  applications: string;
  prompts: string[];
  challenge: string;
  solution: string;
  verificationTitle: string;
  verificationDescription: string;
  packagingTitle: string;
  packagingDescription: string;
  sourcingTitle: string;
  sourcingDescription: string;
  sourcingItems: Array<{ label: string; detail: string }>;
  quoteCta: string;
  planCta: string;
  allApplications: string;
  relatedProductsTitle: string;
  relatedProductsDescription: string;
  viewProduct: string;
  faqTitle: string;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, applicationSlug } = await params;
  const application = await getApplicationBySlug(applicationSlug, locale);
  if (!application) return { title: "Not Found" };

  const pagePath = `/applications/${application.slug}`;
  const canonical = buildCanonicalUrl(pagePath);

  // hreflang: fetch all published locale variants of this slug
  const localeVariants = await getApplicationLocales(application.slug).catch(() => []);
  const languages = buildLocaleAlternates(pagePath, localeVariants);

  const title = application.seo_title ?? application.application_name;
  const description = application.seo_description ?? application.description ?? undefined;
  const ogImage = application.og_image_url ?? application.hero_image_url ?? undefined;

  return {
    title,
    description,
    alternates: {
      canonical,
      languages,
    },
    openGraph: {
      title,
      description,
      url: canonical,
      images: ogImage ? [{ url: ogImage, width: 1200, height: 630, alt: title }] : undefined,
    },
    twitter: buildTwitterMeta({ title, description, imageUrl: ogImage ?? null }),
  };
}

export default async function ApplicationDetailPage({ params }: Props) {
  const { locale, applicationSlug } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<ApplicationDetailMessages>("applicationDetail"),
  ]);
  const application = await getApplicationBySlug(applicationSlug, locale);
  if (!application) notFound();

  // Fetch M2M linked products and FAQs (1a.5.12 内連自動化)
  const [relatedProducts, relatedFaqs] = await Promise.all([
    getApplicationRelatedProducts(application.id).catch(() => []),
    getApplicationRelatedFAQs(application.id).catch(() => []),
  ]);
  const heroImage = getApplicationImage(application.slug, application.hero_image_url);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [application, ...relatedProducts, ...relatedFaqs]);

  return (
    <>
      <PageViewTracker pageType="application" pageId={application.id} />
      <ChatWidget
        contextPage={`/applications/${application.slug}`}
        contextEntityType="application"
        contextEntityId={application.id}
      />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.applications, url: `${SITE_URL}/applications` },
          {
            name: application.application_name,
            url: `${SITE_URL}/applications/${application.slug}`,
          },
        ])}
      />

      {/* Hero */}
      <section
        className="relative overflow-hidden bg-gradient-to-br from-slate-800 to-slate-600 text-white py-16"
        style={
          heroImage
            ? {
                backgroundImage: `url(${heroImage})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : undefined
        }
      >
        {heroImage && (
          <div className="absolute inset-0 bg-slate-900/70" aria-hidden="true" />
        )}
        <div className="relative container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-4 text-xs text-slate-300">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/applications" className="hover:underline">{copy.applications}</Link>
            <span className="mx-1">/</span>
            <span>{application.application_name}</span>
          </nav>
          <span className="inline-block rounded-full bg-blue-600/80 px-3 py-0.5 text-xs font-medium mb-3">
            {application.industry}
          </span>
          <h1 className="text-3xl font-bold sm:text-4xl">{application.application_name}</h1>
          {application.description && (
            <div
              className="mt-4 max-w-2xl text-slate-200 leading-relaxed prose prose-invert prose-p:my-2"
              dangerouslySetInnerHTML={{ __html: application.description }}
            />
          )}
        </div>
      </section>

      {/* Challenge & Solution */}
      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          <div className="mb-8 grid gap-4 md:grid-cols-3">
            {copy.prompts.map((item) => (
              <div key={item} className="rounded-xl border border-gray-200 bg-gray-50 p-4 text-sm leading-relaxed text-gray-600">
                {item}
              </div>
            ))}
          </div>

          {(application.challenge || application.solution) && (
            <div className="grid gap-8 lg:grid-cols-2">
              {application.challenge && (
                <div className="rounded-xl border border-orange-100 bg-orange-50 p-6">
                  <h2 className="text-lg font-semibold text-orange-800 mb-3">
                    {copy.challenge}
                  </h2>
                  <div
                    className="text-gray-700 text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4"
                    dangerouslySetInnerHTML={{ __html: application.challenge }}
                  />
                </div>
              )}
              {application.solution && (
                <div className="rounded-xl border border-green-100 bg-green-50 p-6">
                  <h2 className="text-lg font-semibold text-green-800 mb-3">{copy.solution}</h2>
                  <div
                    className="text-gray-700 text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4"
                    dangerouslySetInnerHTML={{ __html: application.solution }}
                  />
                </div>
              )}
            </div>
          )}

          <div className="mt-10 grid gap-6 lg:grid-cols-2">
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={QUALITY_INSPECTION_IMAGE}
                alt={`${siteConfig.brandName} quality inspection workflow`}
                className="h-56 w-full object-cover"
              />
              <div className="p-5">
                <h2 className="text-base font-semibold text-gray-900">{copy.verificationTitle}</h2>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">
                  {copy.verificationDescription}
                </p>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={CUSTOM_PACKAGING_IMAGE}
                alt={`${siteConfig.brandName} OEM and private-label packaging support`}
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

          {/* Sourcing Considerations */}
          <div className="mt-10 rounded-2xl border border-gray-200 bg-gray-50 p-6">
            <h2 className="text-base font-semibold text-gray-900">{copy.sourcingTitle}</h2>
            <p className="mt-1 text-sm text-gray-500">{copy.sourcingDescription}</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              {copy.sourcingItems.map((item) => (
                <div key={item.label} className="flex gap-3">
                  <svg className="mt-0.5 h-4 w-4 shrink-0 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div>
                    <p className="text-sm font-semibold text-gray-800">{item.label}</p>
                    <p className="mt-0.5 text-xs leading-relaxed text-gray-500">{item.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="mt-6 flex flex-wrap gap-4">
            <Link
              href={`/rfq?application_id=${application.id}`}
              className="rounded-lg bg-blue-700 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              {copy.quoteCta}
            </Link>
            <Link
              href="/contact"
              className="rounded-lg border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copy.planCta}
            </Link>
            <Link
              href="/applications"
              className="rounded-lg border border-gray-200 px-6 py-3 text-sm text-gray-500 hover:bg-gray-50 transition-colors"
            >
              {copy.allApplications}
            </Link>
          </div>
        </div>
      </section>

      {/* Related Products (M2M) */}
      {relatedProducts.length > 0 && (
        <section className="bg-gray-50 py-14">
          <div className="container mx-auto max-w-5xl px-6">
            <h2 className="text-xl font-bold text-gray-800 mb-2">{copy.relatedProductsTitle}</h2>
            <p className="mb-6 max-w-2xl text-sm leading-relaxed text-gray-500">
              {copy.relatedProductsDescription}
            </p>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {relatedProducts.map((product) => (
                <Link
                  key={product.id}
                  href={product.category_slug ? `/products/${product.category_slug}/${product.slug}` : "/products"}
                  className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="mb-4 overflow-hidden rounded-lg bg-slate-100 aspect-[4/3]">
                    {product.model_number ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={getProductImage({ model_number: product.model_number }, product.category_slug) ?? undefined}
                        alt={product.product_name}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-slate-300">
                        <svg className="h-12 w-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                      </div>
                    )}
                  </div>
                  {product.model_number && (
                    <p className="text-xs font-mono text-gray-400">{product.model_number}</p>
                  )}
                  <h3 className="mt-1 font-semibold text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2">
                    {product.product_name}
                  </h3>
                  {product.short_description && (
                    <p className="mt-2 text-sm text-gray-500 line-clamp-2">
                      {product.short_description}
                    </p>
                  )}
                  <span className="mt-3 inline-block text-xs text-blue-600 group-hover:underline">
                    {copy.viewProduct}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Application-specific FAQs (M2M) */}
      {relatedFaqs.length > 0 && (
        <section className="py-14">
          <div className="container mx-auto max-w-5xl px-6">
            <h2 className="text-xl font-bold text-gray-800 mb-6">
              {copy.faqTitle}
            </h2>
            <FAQAccordion
              items={relatedFaqs.map((f) => ({
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
              }))}
            />
          </div>
        </section>
      )}
    </>
  );
}
