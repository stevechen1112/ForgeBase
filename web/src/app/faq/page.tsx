import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedFAQs } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema, buildFAQSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

export const metadata: Metadata = {
  title: "Frequently Asked Questions",
  description:
    "Find answers to common questions about our products, certifications, MOQ, lead times, and technical specifications.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export default async function FAQPage() {
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
            Everything you need to know about our products, quality standards, and ordering process.
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
        </div>
      </section>
    </>
  );
}
