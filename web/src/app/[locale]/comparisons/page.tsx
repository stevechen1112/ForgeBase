import type { Metadata } from "next";
import { getPublishedComparisons } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";

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

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<ComparisonsPageMessages>("comparisons").then((copy) => copy.metadata);
}

export default async function ComparisonsPage({ params }: Props) {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const comparisons = await getPublishedComparisons(resolvedLocale);
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<ComparisonsPageMessages>("comparisons"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, comparisons);

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
