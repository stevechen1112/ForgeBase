import type { Metadata } from "next";
import { getPublishedCapabilities } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
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

type CapabilitiesPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  tags: string[];
  ctaTitle: string;
  ctaDescription: string;
  ctaPrimary: string;
  ctaSecondary: string;
  buyerBenefit: Record<string, string>;
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<CapabilitiesPageMessages>("capabilities").then((copy) => copy.metadata);
}

export default async function CapabilitiesPage({ params }: Props) {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const capabilities = await getPublishedCapabilities(resolvedLocale);
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<CapabilitiesPageMessages>("capabilities"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, capabilities);

  if (siteConfig.layout === "industrial") {
    return (
      <>
        <PageViewTracker pageType="capability" />
        <StructuredData data={buildBreadcrumbSchema([{ name: common.home, url: SITE_URL }, { name: pageCopy.breadcrumb, url: `${SITE_URL}/capabilities` }])} />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: pageCopy.breadcrumb },
            ]}
            eyebrow="Operations"
            title={pageCopy.title}
            description={pageCopy.description}
          >
            <div className="flex flex-wrap gap-2 text-[11px] font-black uppercase tracking-[0.16em] text-gray-400">
              {pageCopy.tags.map((tag) => (
                <span key={tag} className="border border-gray-700 px-3 py-1">{tag}</span>
              ))}
            </div>
          </IndustrialPageHero>
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {capabilities.map((cap) => {
                  const buyerBenefit = cap.category_tag ? (pageCopy.buyerBenefit[cap.category_tag.toLowerCase() as keyof typeof pageCopy.buyerBenefit] ?? null) : null;
                  return (
                    <Link key={cap.id} href={`/capabilities/${cap.slug}`} className="group border border-gray-300 bg-white p-5 transition-colors hover:border-primary/50 hover:bg-primary/5">
                      {cap.category_tag && (
                        <span className="mb-3 inline-block bg-primary px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-primary-foreground">
                          {cap.category_tag}
                        </span>
                      )}
                      <h2 className="text-base font-black uppercase tracking-wide text-gray-900 transition-colors group-hover:text-primary">{cap.capability_name}</h2>
                      <p className="mt-2 text-sm text-gray-500">{cap.short_description}</p>
                      {buyerBenefit && (
                        <p className="mt-4 border-t border-gray-200 pt-4 text-xs leading-relaxed text-gray-600">{buyerBenefit}</p>
                      )}
                    </Link>
                  );
                })}
              </div>
              <div className="mt-12">
                <IndustrialCtaPanel
                  title={pageCopy.ctaTitle}
                  description={pageCopy.ctaDescription}
                  primaryHref="/contact"
                  primaryLabel={pageCopy.ctaPrimary}
                  secondaryHref="/rfq"
                  secondaryLabel={pageCopy.ctaSecondary}
                />
              </div>
            </div>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <PageViewTracker pageType="capability" />
      <StructuredData data={buildBreadcrumbSchema([{ name: common.home, url: SITE_URL }, { name: pageCopy.breadcrumb, url: `${SITE_URL}/capabilities` }])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{pageCopy.breadcrumb}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{pageCopy.title}</h1>
          <p className="mt-2 max-w-2xl text-gray-500">
            {pageCopy.description}
          </p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs text-gray-400">
            {pageCopy.tags.map((tag) => (
              <span key={tag} className="rounded-full border border-gray-200 bg-white px-3 py-1">{tag}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap) => {
              const buyerBenefit = cap.category_tag ? (pageCopy.buyerBenefit[cap.category_tag.toLowerCase() as keyof typeof pageCopy.buyerBenefit] ?? null) : null;
              return (
                <Link key={cap.id} href={`/capabilities/${cap.slug}`} className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all">
                  {cap.category_tag && (
                    <span className="mb-2 inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-blue-600">
                      {cap.category_tag}
                    </span>
                  )}
                  <h2 className="font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{cap.capability_name}</h2>
                  <p className="mt-2 text-sm text-gray-500">{cap.short_description}</p>
                  {buyerBenefit && (
                    <p className="mt-3 text-xs text-blue-600 border-t border-gray-100 pt-3">{buyerBenefit}</p>
                  )}
                </Link>
              );
            })}
          </div>

          <div className="mt-10 rounded-2xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">{pageCopy.ctaTitle}</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-blue-800">
              {pageCopy.ctaDescription}
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/contact" className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                {pageCopy.ctaPrimary}
              </Link>
              <Link href="/rfq" className="rounded-lg border border-blue-300 bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 transition-colors">
                {pageCopy.ctaSecondary}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}