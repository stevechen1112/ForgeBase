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
import { siteConfig } from "@/lib/siteConfig";
import { IndustrialCtaPanel, IndustrialPageHero } from "@/components/themes";

type CommonMessages = {
  home: string;
};

type FAQPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  emptyState: string;
  ctaTitle: string;
  ctaDescription: string;
  ctaButtons: {
    rfq: string;
    contact: string;
    applications: string;
  };
};

interface Props {
  params: Promise<{ locale: string }>;
}

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  await params;
  return getMessageNamespace<FAQPageMessages>("faqPage").then((copy) => copy.metadata);
}

export default async function FAQPage({ params }: Props) {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const faqs = await getPublishedFAQs(resolvedLocale);
  const [copy, common] = await Promise.all([
    getMessageNamespace<FAQPageMessages>("faqPage"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, faqs);

  // Group by category_tag
  const grouped = faqs.reduce<Record<string, typeof faqs>>((acc, faq) => {
    const key = faq.category_tag ?? "General";
    if (!acc[key]) acc[key] = [];
    acc[key].push(faq);
    return acc;
  }, {});

  const tags = Object.keys(grouped).sort();

  if (siteConfig.layout === "industrial") {
    return (
      <>
        <PageViewTracker pageType="faq" />
        <ChatWidget contextPage="/faq" contextEntityType="faq" />
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: copy.breadcrumb, url: `${SITE_URL}/faq` },
          ])}
        />
        {faqs.length > 0 && <StructuredData data={buildFAQSchema(faqs)} />}
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: copy.breadcrumb },
            ]}
            eyebrow="Buyer Questions"
            title={copy.title}
            description={copy.description}
          >
            {tags.length > 1 && (
              <div className="flex flex-wrap gap-2">
                {tags.map((tag) => (
                  <Link
                    key={tag}
                    href={`/faq/${encodeURIComponent(tag.toLowerCase().replace(/\s+/g, "-"))}`}
                    className="border border-gray-700 px-3 py-1 text-[11px] font-black uppercase tracking-[0.16em] text-gray-300 hover:border-primary hover:text-primary"
                  >
                    {tag} ({grouped[tag].length})
                  </Link>
                ))}
              </div>
            )}
          </IndustrialPageHero>
          <section className="py-16">
            <div className="mx-auto max-w-4xl px-6 space-y-10">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} />}
              {faqs.length === 0 ? (
                <p className="border border-dashed border-gray-300 bg-gray-50 py-16 text-center text-sm text-gray-500">{copy.emptyState}</p>
              ) : (
                tags.map((tag) => (
                  <div key={tag}>
                    <div className="mb-4 flex items-center gap-3">
                      <div className="h-6 w-1.5 bg-primary" />
                      <h2 className="text-sm font-black uppercase tracking-[0.18em] text-gray-900" id={tag.toLowerCase().replace(/\s+/g, "-")}>{tag}</h2>
                    </div>
                    <FAQAccordion items={grouped[tag]} />
                  </div>
                ))
              )}
              <IndustrialCtaPanel
                title={copy.ctaTitle}
                description={copy.ctaDescription}
                primaryHref="/rfq"
                primaryLabel={copy.ctaButtons.rfq}
                secondaryHref="/contact"
                secondaryLabel={copy.ctaButtons.contact}
              />
            </div>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <PageViewTracker pageType="faq" />
      <ChatWidget contextPage="/faq" contextEntityType="faq" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.breadcrumb, url: `${SITE_URL}/faq` },
        ])}
      />
      {faqs.length > 0 && (
        <StructuredData data={buildFAQSchema(faqs)} />
      )}

      {/* Page header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-3xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{copy.breadcrumb}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{copy.title}</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            {copy.description}
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
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} />}
          {faqs.length === 0 ? (
            <p className="text-center text-gray-500 py-16">{copy.emptyState}</p>
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
            <h2 className="text-lg font-semibold text-blue-900">{copy.ctaTitle}</h2>
            <p className="mt-2 text-sm leading-relaxed text-blue-800">
              {copy.ctaDescription}
            </p>
            <div className="mt-5 flex flex-wrap gap-3">
              <Link
                href="/rfq"
                className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                {copy.ctaButtons.rfq}
              </Link>
              <Link
                href="/contact"
                className="rounded-lg border border-blue-300 bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 transition-colors"
              >
                {copy.ctaButtons.contact}
              </Link>
              <Link
                href="/applications"
                className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {copy.ctaButtons.applications}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
