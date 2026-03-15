import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import {
  getApplicationBySlug,
  getApplicationRelatedProducts,
  getApplicationRelatedFAQs,
  getApplicationLocales,
} from "@/lib/api";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

type Props = { params: Promise<{ applicationSlug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { applicationSlug } = await params;
  const application = await getApplicationBySlug(applicationSlug);
  if (!application) return { title: "Not Found" };

  const canonical = `${SITE_URL}/applications/${application.slug}`;

  // hreflang: fetch all published locale variants of this slug
  const localeVariants = await getApplicationLocales(application.slug).catch(() => []);
  const languages: Record<string, string> = { "x-default": canonical };
  for (const v of localeVariants) {
    const url =
      v.locale === "en"
        ? `${SITE_URL}/applications/${application.slug}`
        : `${SITE_URL}/${v.locale}/applications/${application.slug}`;
    languages[v.locale] = url;
  }
  if (!("en" in languages)) languages.en = canonical;

  return {
    title: application.seo_title ?? application.application_name,
    description:
      application.seo_description ?? application.description ?? undefined,
    alternates: {
      canonical,
      languages: Object.keys(languages).length > 2 ? languages : undefined,
    },
  };
}

export default async function ApplicationDetailPage({ params }: Props) {
  const { applicationSlug } = await params;
  const application = await getApplicationBySlug(applicationSlug);
  if (!application) notFound();

  // Fetch M2M linked products and FAQs (1a.5.12 内連自動化)
  const [relatedProducts, relatedFaqs] = await Promise.all([
    getApplicationRelatedProducts(application.id).catch(() => []),
    getApplicationRelatedFAQs(application.id).catch(() => []),
  ]);

  return (
    <>
      <PageViewTracker pageType="application" pageId={application.id} />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Applications", url: `${SITE_URL}/applications` },
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
          application.hero_image_url
            ? {
                backgroundImage: `url(${application.hero_image_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
              }
            : undefined
        }
      >
        {application.hero_image_url && (
          <div className="absolute inset-0 bg-slate-900/70" aria-hidden="true" />
        )}
        <div className="relative container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-4 text-xs text-slate-300">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/applications" className="hover:underline">Applications</Link>
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
          {(application.challenge || application.solution) && (
            <div className="grid gap-8 lg:grid-cols-2">
              {application.challenge && (
                <div className="rounded-xl border border-orange-100 bg-orange-50 p-6">
                  <h2 className="text-lg font-semibold text-orange-800 mb-3">
                    The Challenge
                  </h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-line">
                    {application.challenge}
                  </p>
                </div>
              )}
              {application.solution && (
                <div className="rounded-xl border border-green-100 bg-green-50 p-6">
                  <h2 className="text-lg font-semibold text-green-800 mb-3">Our Solution</h2>
                  <p className="text-gray-700 leading-relaxed whitespace-pre-line">
                    {application.solution}
                  </p>
                </div>
              )}
            </div>
          )}

          {/* CTA */}
          <div className="mt-10 flex flex-wrap gap-4">
            <Link
              href="/contact"
              className="rounded-lg bg-blue-700 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              Discuss Your Requirements
            </Link>
            <Link
              href="/applications"
              className="rounded-lg border border-gray-300 px-6 py-3 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              ← All Applications
            </Link>
          </div>
        </div>
      </section>

      {/* Related Products (M2M) */}
      {relatedProducts.length > 0 && (
        <section className="bg-gray-50 py-14">
          <div className="container mx-auto max-w-5xl px-6">
            <h2 className="text-xl font-bold text-gray-800 mb-6">Compatible Products</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {relatedProducts.map((product) => (
                <Link
                  key={product.id}
                  href={product.category_slug ? `/products/${product.category_slug}/${product.slug}` : "/products"}
                  className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all"
                >
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
                    View product →
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
              Frequently Asked Questions
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
