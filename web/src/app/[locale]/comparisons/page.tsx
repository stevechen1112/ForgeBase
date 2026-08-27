import type { Metadata } from "next";
import { getPublishedComparisons } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages.server";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type CommonMessages = {
  home: string;
};

type ComparisonsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  emptyState: string;
  readMore: string;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<ComparisonsPageMessages>("comparisons").then((copy) => copy.metadata);
}

export default async function ComparisonsPage({ params }: Props) {
  const { siteUrl: SITE_URL, isIndustrial } = await getRuntimeSiteContext();
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const comparisons = await getPublishedComparisons(resolvedLocale);
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<ComparisonsPageMessages>("comparisons"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, comparisons);

  if (isIndustrial) {
    return (
      <>
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: pageCopy.breadcrumb, url: `${SITE_URL}/comparisons` },
          ])}
        />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: pageCopy.breadcrumb },
            ]}
            eyebrow="Decision Guides"
            title={pageCopy.title}
            description={pageCopy.description}
          />
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
              {comparisons.length === 0 ? (
                <p className="border border-dashed border-gray-300 bg-gray-50 py-16 text-center text-sm text-gray-500">{pageCopy.emptyState}</p>
              ) : (
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {comparisons.map((c) => (
                    <Link
                      key={c.id}
                      href={`/comparisons/${c.slug}`}
                      className="group border border-gray-300 bg-white p-5 transition-colors hover:border-primary/50 hover:bg-primary/5"
                    >
                      <h2 className="text-base font-black uppercase tracking-wide text-gray-900 transition-colors group-hover:text-primary">
                        {c.topic_title}
                      </h2>
                      {c.summary && (
                        <p className="mt-2 text-sm text-gray-500 line-clamp-3">{c.summary}</p>
                      )}
                      <p className="mt-4 text-[11px] font-black uppercase tracking-[0.16em] text-primary group-hover:underline">
                        {pageCopy.readMore}
                      </p>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: pageCopy.breadcrumb, url: `${SITE_URL}/comparisons` },
        ])}
      />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{pageCopy.breadcrumb}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{pageCopy.title}</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            {pageCopy.description}
          </p>
        </div>
      </section>

      {/* Comparison cards */}
      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          {comparisons.length === 0 ? (
            <p className="text-center text-gray-500 py-16">{pageCopy.emptyState}</p>
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
                    {pageCopy.readMore}
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
