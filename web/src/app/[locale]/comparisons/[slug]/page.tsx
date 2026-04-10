import { notFound } from "next/navigation";
import { Link } from "@/i18n/navigation";
import type { Metadata } from "next";
import { getPublishedComparisons, getComparisonBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { siteConfig } from "@/lib/siteConfig";
import { IndustrialCtaPanel, IndustrialPageHero } from "@/components/themes";

type Props = { params: Promise<{ locale: string; slug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

type CommonMessages = {
  home: string;
};

type ComparisonDetailMessages = {
  comparisons: string;
  dimension: string;
  optionA: string;
  optionB: string;
  detailsTitle: string;
  takeawayTitle: string;
  recommendedTitle: string;
  recommendedDescription: string;
  rfqTitle: string;
  rfqDescription: string;
  submitRfq: string;
  askQuestion: string;
  allComparisons: string;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const topic = await getComparisonBySlug(slug);
  if (!topic) return {};
  return {
    title: topic.seo_title ?? topic.topic_title,
    description: topic.seo_description ?? topic.summary ?? undefined,
  };
}

export async function generateStaticParams() {
  const comparisons = await getPublishedComparisons("en");
  return comparisons.map((c) => ({ slug: c.slug }));
}

export default async function ComparisonDetailPage({ params }: Props) {
  const { locale, slug } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<ComparisonDetailMessages>("comparisonDetail"),
  ]);
  const topic = await getComparisonBySlug(slug);
  if (!topic) notFound();
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [topic]);

  // Parse dimensions JSON if stored as string
  // Actual seed schema: { dimension, our_value, competitor_value, winner }
  type DimRow = { dimension: string; our_value: string; competitor_value: string; winner?: string };
  let dimensions: DimRow[] | null = null;
  if (topic.dimensions) {
    try {
      const parsed = JSON.parse(topic.dimensions);
      dimensions = Array.isArray(parsed) ? parsed : null;
    } catch {
      // not JSON, treat as plain text
    }
  }

  if (siteConfig.layout === "industrial") {
    return (
      <>
        <PageViewTracker pageType="comparison" pageId={topic.id} />
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: copy.comparisons, url: `${SITE_URL}/comparisons` },
            { name: topic.topic_title, url: `${SITE_URL}/comparisons/${slug}` },
          ])}
        />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: copy.comparisons, href: "/comparisons" },
              { label: topic.topic_title },
            ]}
            eyebrow="Comparison"
            title={topic.topic_title}
            description={topic.summary ?? undefined}
          />
          <section className="py-16">
            <div className="mx-auto max-w-5xl px-6 space-y-10">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} />}
              {dimensions ? (
                <div className="overflow-x-auto border border-gray-300">
                  <table className="w-full text-sm">
                    <thead className="border-b border-gray-300 bg-gray-900 text-white">
                      <tr>
                        <th className="px-4 py-3 text-left text-[11px] font-black uppercase tracking-[0.16em]">{copy.dimension}</th>
                        <th className="px-4 py-3 text-left text-[11px] font-black uppercase tracking-[0.16em]">{copy.optionA}</th>
                        <th className="px-4 py-3 text-left text-[11px] font-black uppercase tracking-[0.16em]">{copy.optionB}</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {dimensions.map((dim) => (
                        <tr key={dim.dimension} className="bg-white hover:bg-gray-50">
                          <td className="px-4 py-3 font-medium text-gray-700">{dim.dimension}</td>
                          <td className={`px-4 py-3 ${dim.winner === "us" ? "font-black text-primary" : "text-gray-600"}`}>{dim.our_value}</td>
                          <td className="px-4 py-3 text-gray-600">{dim.competitor_value}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : topic.dimensions ? (
                <div className="border border-gray-300 bg-white p-6">
                  <h2 className="mb-3 text-base font-black uppercase tracking-wide text-gray-900">{copy.detailsTitle}</h2>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{topic.dimensions}</p>
                </div>
              ) : null}
              {topic.conclusion && (
                <div className="border-l-4 border-primary bg-gray-50 p-6">
                  <h2 className="mb-2 text-base font-black uppercase tracking-wide text-gray-900">{copy.takeawayTitle}</h2>
                  <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{topic.conclusion}</p>
                </div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="border border-gray-300 bg-white p-5">
                  <h2 className="text-sm font-black uppercase tracking-wide text-gray-900">{copy.recommendedTitle}</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{copy.recommendedDescription}</p>
                </div>
                <div className="border-l-4 border-primary bg-gray-50 p-5">
                  <h2 className="text-sm font-black uppercase tracking-wide text-gray-900">{copy.rfqTitle}</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{copy.rfqDescription}</p>
                </div>
              </div>
              <IndustrialCtaPanel
                title={copy.rfqTitle}
                description={copy.rfqDescription}
                primaryHref="/rfq"
                primaryLabel={copy.submitRfq}
                secondaryHref="/contact"
                secondaryLabel={copy.askQuestion}
              />
              <div>
                <Link href="/comparisons" className="text-[11px] font-black uppercase tracking-[0.16em] text-primary hover:underline">{copy.allComparisons}</Link>
              </div>
            </div>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <PageViewTracker pageType="comparison" pageId={topic.id} />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.comparisons, url: `${SITE_URL}/comparisons` },
          { name: topic.topic_title, url: `${SITE_URL}/comparisons/${slug}` },
        ])}
      />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/comparisons" className="hover:underline">{copy.comparisons}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{topic.topic_title}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{topic.topic_title}</h1>
          {topic.summary && (
            <p className="mt-3 text-gray-500 max-w-2xl">{topic.summary}</p>
          )}
        </div>
      </section>

      {/* Comparison table or plain text dimensions */}
      <section className="py-14">
        <div className="container mx-auto max-w-4xl px-6 space-y-10">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} />}
          {dimensions ? (
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">{copy.dimension}</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">{copy.optionA}</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">{copy.optionB}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {dimensions.map((dim) => (
                    <tr key={dim.dimension} className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-700">{dim.dimension}</td>
                      <td className={`px-4 py-3 text-gray-600 ${dim.winner === "us" ? "font-semibold text-blue-700" : ""}`}>{dim.our_value}</td>
                      <td className="px-4 py-3 text-gray-600">{dim.competitor_value}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : topic.dimensions ? (
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-base font-semibold text-gray-700 mb-3">{copy.detailsTitle}</h2>
              <p className="text-sm text-gray-600 whitespace-pre-line leading-relaxed">{topic.dimensions}</p>
            </div>
          ) : null}

          {/* Conclusion */}
          {topic.conclusion && (
            <div className="rounded-xl bg-blue-50 border border-blue-100 p-6">
              <h2 className="text-base font-semibold text-blue-800 mb-2">{copy.takeawayTitle}</h2>
              <p className="text-sm text-blue-700 leading-relaxed whitespace-pre-line">{topic.conclusion}</p>
            </div>
          )}

          {/* Recommended for / When to RFQ */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">{copy.recommendedTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                {copy.recommendedDescription}
              </p>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h2 className="text-sm font-semibold text-blue-900">{copy.rfqTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-800">
                {copy.rfqDescription}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-5">
            <Link
              href="/rfq"
              className="rounded-lg bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              {copy.submitRfq}
            </Link>
            <Link
              href="/contact"
              className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              {copy.askQuestion}
            </Link>
            <Link href="/comparisons" className="ml-auto text-sm text-blue-600 hover:underline">
              {copy.allComparisons}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
