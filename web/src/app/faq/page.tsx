import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedFAQs } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema, buildFAQSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();

  return {
    title: "Frequently Asked Questions",
    description:
      `Find answers to common questions about ${siteName} MOQ, lead times, OEM packaging, compliance support, sampling, and technical documentation.`,
  };
}

export default async function FAQPage() {
  const { siteUrl: SITE_URL } = await getRuntimeSiteContext();
  const faqs = await getPublishedFAQs("en");

  // Group by category_tag
  const grouped = faqs.reduce<Record<string, typeof faqs>>((acc, faq) => {
    const key = faq.category_tag ?? "General";
    if (!acc[key]) acc[key] = [];
    acc[key].push(faq);
    return acc;
  }, {});

  const tags = Object.keys(grouped).sort();

  return (
    <>
      <PageViewTracker pageType="faq" />
      <ChatWidget contextPage="/faq" contextEntityType="faq" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "FAQ", url: `${SITE_URL}/faq` },
        ])}
      />
      {faqs.length > 0 && (
        <StructuredData data={buildFAQSchema(faqs)} />
      )}

      {/* Page header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-3xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">FAQ</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">Frequently Asked Questions</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            This FAQ is built for buyers who need clearer answers on ordering flow, sampling, packaging, documentation, and repeat-order execution before reaching out.
          </p>

          {/* Tag filter links */}
          {tags.length > 1 && (
            <div className="mt-5 flex flex-wrap gap-2">
              {tags.map((tag) => (
                <Link
                  key={tag}
                  href={`/faq/${encodeURIComponent(tag.toLowerCase().replace(/\s+/g, "-"))}`}
                  className="rounded-full border border-gray-200 bg-white px-3 py-1 text-xs text-gray-600 hover:border-blue-500 hover:text-blue-600 transition-colors"
                >
                  {tag} ({grouped[tag].length})
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* FAQ sections */}
      <section className="py-14">
        <div className="container mx-auto max-w-3xl px-6 space-y-10">
          {faqs.length === 0 ? (
            <p className="text-center text-gray-500 py-16">No FAQs published yet.</p>
          ) : (
            tags.map((tag) => (
              <div key={tag}>
                <h2 className="mb-4 text-lg font-semibold text-gray-700" id={tag.toLowerCase().replace(/\s+/g, "-")}>
                  {tag}
                </h2>
                <FAQAccordion items={grouped[tag]} />
              </div>
            ))
          )}

          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">Ready for the next step?</h2>
            <p className="mt-2 text-sm leading-relaxed text-blue-800">
              Use FAQ for general policy questions, Contact for exploratory business discussions, and RFQ when you have product scope, quantity, packaging, or market requirements ready to send through.
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/rfq"
                className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                Submit RFQ →
              </Link>
              <Link
                href="/contact"
                className="rounded-lg border border-blue-300 bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
              >
                Ask a Question
              </Link>
              <Link
                href="/applications"
                className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                Browse by Application
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
