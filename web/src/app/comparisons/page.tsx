import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedComparisons } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";

export const metadata: Metadata = {
  title: "Product Comparisons",
  description:
    "Comparison guides for hand tool buyers evaluating material, format, and sourcing tradeoffs before product selection or RFQ.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export default async function ComparisonsPage() {
  const comparisons = await getPublishedComparisons("en");

  return (
    <>
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Comparisons", url: `${SITE_URL}/comparisons` },
        ])}
      />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Comparisons</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">Product Comparisons</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            These guides are written for buyers who need faster decision support on tool format, material, compliance fit, and sourcing practicality.
          </p>
        </div>
      </section>

      {/* Comparison cards */}
      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {comparisons.length === 0 ? (
            <p className="text-center text-gray-500 py-16">No comparisons published yet.</p>
          ) : (
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {comparisons.map((c) => (
                <Link
                  key={c.id}
                  href={`/comparisons/${c.slug}`}
                  className="group rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md hover:border-blue-300 transition-all"
                >
                  <h2 className="text-base font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                    {c.topic_title}
                  </h2>
                  {c.summary && (
                    <p className="mt-2 text-sm text-gray-500 line-clamp-3">{c.summary}</p>
                  )}
                  <p className="mt-4 text-xs font-medium text-blue-600 group-hover:underline">
                    Read comparison →
                  </p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
