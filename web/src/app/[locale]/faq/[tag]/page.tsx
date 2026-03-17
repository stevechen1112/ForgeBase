import { notFound } from "next/navigation";
import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedFAQs } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema, buildFAQSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

type Props = { params: Promise<{ locale: string; tag: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { tag } = await params;
  const decoded = decodeURIComponent(tag).replace(/-/g, " ");
  const label = decoded.charAt(0).toUpperCase() + decoded.slice(1);
  return {
    title: `${label} — FAQ`,
    description: `Frequently asked questions about ${label.toLowerCase()}.`,
  };
}

export async function generateStaticParams() {
  const faqs = await getPublishedFAQs("en");
  const tags = [...new Set(faqs.map((f) => f.category_tag).filter(Boolean))] as string[];
  return tags.map((tag) => ({ tag: encodeURIComponent(tag.toLowerCase().replace(/\s+/g, "-")) }));
}

export default async function FAQTagPage({ params }: Props) {
  const { locale, tag } = await params;
  const decoded = decodeURIComponent(tag).replace(/-/g, " ");

  const allFaqs = await getPublishedFAQs(locale);
  const filtered = allFaqs.filter(
    (f) => (f.category_tag ?? "general").toLowerCase().replace(/\s+/g, "-") === tag.toLowerCase()
  );

  if (filtered.length === 0) notFound();

  const label = decoded.charAt(0).toUpperCase() + decoded.slice(1);

  return (
    <>
      <PageViewTracker pageType="faq" pageId={tag} />
      <ChatWidget contextPage={`/faq/${tag}`} contextEntityType="faq" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "FAQ", url: `${SITE_URL}/faq` },
          { name: label, url: `${SITE_URL}/faq/${tag}` },
        ])}
      />
      <StructuredData data={buildFAQSchema(filtered)} />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-3xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/faq" className="hover:underline">FAQ</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{label}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{label} — FAQ</h1>
          <p className="mt-1 text-sm text-gray-500">{filtered.length} questions</p>
        </div>
      </section>

      {/* FAQ list */}
      <section className="py-14">
        <div className="container mx-auto max-w-3xl px-6">
          <FAQAccordion items={filtered} />
          <div className="mt-8">
            <Link href="/faq" className="text-sm text-blue-600 hover:underline">← All FAQ categories</Link>
          </div>
        </div>
      </section>
    </>
  );
}
