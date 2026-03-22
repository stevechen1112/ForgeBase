import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getPublishedFAQs } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FAQAccordion } from "@/components/ui/FAQAccordion";
import { StructuredData, buildBreadcrumbSchema, buildFAQSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";

type Props = { params: Promise<{ locale: string; tag: string }> };

type CommonMessages = {
  home: string;
  questions: string;
};

type FaqPageMessages = {
  breadcrumb: string;
  allCategories: string;
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, tag } = await params;
  resolveLocale(locale);
  const copy = await getMessageNamespace<FaqPageMessages>("faqPage");
  const decoded = decodeURIComponent(tag).replace(/-/g, " ");
  const label = decoded.charAt(0).toUpperCase() + decoded.slice(1);
  return {
    title: `${label} - ${copy.breadcrumb}`,
    description: `${copy.breadcrumb}: ${label}`,
  };
}

export async function generateStaticParams() {
  const faqs = await getPublishedFAQs("en");
  const tags = [...new Set(faqs.map((f) => f.category_tag).filter(Boolean))] as string[];
  return tags.map((tag) => ({ tag: encodeURIComponent(tag.toLowerCase().replace(/\s+/g, "-")) }));
}

export default async function FAQTagPage({ params }: Props) {
  const { locale, tag } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<FaqPageMessages>("faqPage"),
  ]);
  const decoded = decodeURIComponent(tag).replace(/-/g, " ");

  const allFaqs = await getPublishedFAQs(resolvedLocale);
  const filtered = allFaqs.filter(
    (f) => (f.category_tag ?? "general").toLowerCase().replace(/\s+/g, "-") === tag.toLowerCase()
  );

  if (filtered.length === 0) notFound();

  const label = decoded.charAt(0).toUpperCase() + decoded.slice(1);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, filtered);

  return (
    <>
      <PageViewTracker pageType="faq" pageId={tag} />
      <ChatWidget contextPage={`/faq/${tag}`} contextEntityType="faq" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.breadcrumb, url: `${SITE_URL}/faq` },
          { name: label, url: `${SITE_URL}/faq/${tag}` },
        ])}
      />
      <StructuredData data={buildFAQSchema(filtered)} />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-3xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/faq" className="hover:underline">{copy.breadcrumb}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{label}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{label} - {copy.breadcrumb}</h1>
          <p className="mt-1 text-sm text-gray-500">{filtered.length} {common.questions}</p>
        </div>
      </section>

      {/* FAQ list */}
      <section className="py-14">
        <div className="container mx-auto max-w-3xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          <FAQAccordion items={filtered} />
          <div className="mt-8">
            <Link href="/faq" className="text-sm text-blue-600 hover:underline">{copy.allCategories}</Link>
          </div>
        </div>
      </section>
    </>
  );
}
