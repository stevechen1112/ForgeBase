import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedComparisons, getComparisonBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

type Props = { params: Promise<{ locale: string; slug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

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
  const { slug } = await params;
  const topic = await getComparisonBySlug(slug);
  if (!topic) notFound();

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

  return (
    <>
      <PageViewTracker pageType="comparison" pageId={topic.id} />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Comparisons", url: `${SITE_URL}/comparisons` },
          { name: topic.topic_title, url: `${SITE_URL}/comparisons/${slug}` },
        ])}
      />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/comparisons" className="hover:underline">Comparisons</Link>
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
          {dimensions ? (
            <div className="overflow-x-auto rounded-xl border border-gray-200">
              <table className="w-full text-sm">
                <thead className="bg-gray-50 border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Dimension</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Option A</th>
                    <th className="px-4 py-3 text-left font-medium text-gray-600">Option B</th>
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
              <h2 className="text-base font-semibold text-gray-700 mb-3">Comparison Details</h2>
              <p className="text-sm text-gray-600 whitespace-pre-line leading-relaxed">{topic.dimensions}</p>
            </div>
          ) : null}

          {/* Conclusion */}
          {topic.conclusion && (
            <div className="rounded-xl bg-blue-50 border border-blue-100 p-6">
              <h2 className="text-base font-semibold text-blue-800 mb-2">Buyer Takeaway</h2>
              <p className="text-sm text-blue-700 leading-relaxed whitespace-pre-line">{topic.conclusion}</p>
            </div>
          )}

          {/* Recommended for / When to RFQ */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-gray-50 p-5">
              <h2 className="text-sm font-semibold text-gray-900">Recommended for</h2>
              <p className="mt-2 text-sm leading-relaxed text-gray-600">
                Buyers who have narrowed down format options and need a clearer basis for supplier discussions, specification alignment, or private-label program planning. Use this comparison as a reference point when briefing your team or building an RFQ scope.
              </p>
            </div>
            <div className="rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h2 className="text-sm font-semibold text-blue-900">When to move to RFQ</h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-800">
                Once you have a preferred direction from this comparison, include key parameters in your RFQ: target quantity, OEM scope, preferred market, and required compliance standard. NorthForge can shortlist the right SKU or material spec from there.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-4 rounded-xl border border-gray-200 bg-white p-5">
            <Link
              href="/rfq"
              className="rounded-lg bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
            >
              Submit Your RFQ →
            </Link>
            <Link
              href="/contact"
              className="rounded-lg border border-gray-300 px-6 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
            >
              Ask a Sourcing Question
            </Link>
            <Link href="/comparisons" className="ml-auto text-sm text-blue-600 hover:underline">
              ← All comparisons
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
