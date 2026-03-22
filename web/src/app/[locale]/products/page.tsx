import type { Metadata } from "next";
import { getPublishedCategories } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { StructuredData } from "@/components/seo/StructuredData";
import { PRODUCTS_HERO_IMAGE, getCategoryCardImage } from "@/lib/demoAssets";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";

type CommonMessages = {
  home: string;
};

type ProductsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  heroTitle: string;
  heroDescription: string;
  highlights: Array<{ label: string; desc: string }>;
  browseLabel: string;
  categoriesTitle: string;
  contactCta: string;
  emptyState: string;
  emptyCta: string;
  viewProducts: string;
  customTitle: string;
  customDescription: string;
  customCta: string;
  talkCta: string;
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<ProductsPageMessages>("products").then((copy) => copy.metadata);
}

export default async function ProductsPage({ params }: Props) {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const categories = await getPublishedCategories(resolvedLocale);
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<ProductsPageMessages>("products"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, categories);

  return (
    <>
      <ChatWidget contextPage="/products" contextEntityType="category" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: pageCopy.breadcrumb, url: `${SITE_URL}/products` },
        ])}
      />

      {/* ── Hero header ── */}
      <section className="relative overflow-hidden border-b border-gray-100 py-16 text-white">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${PRODUCTS_HERO_IMAGE})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/85 via-blue-950/78 to-blue-900/55" />
        <div className="mx-auto max-w-6xl px-6">
          <nav aria-label="Breadcrumb" className="relative mb-4 text-xs text-blue-300">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1.5">/</span>
            <span>{pageCopy.breadcrumb}</span>
          </nav>
          <h1 className="relative text-4xl font-extrabold">{pageCopy.heroTitle}</h1>
          <p className="relative mt-3 max-w-xl text-lg text-blue-200 leading-relaxed">
            {pageCopy.heroDescription}
          </p>
        </div>
      </section>

      {/* ── Quick highlights ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-2 divide-x divide-y divide-gray-100 sm:grid-cols-4 sm:divide-y-0">
            {pageCopy.highlights.map((h) => (
              <div key={h.label} className="flex flex-col items-center py-6 text-center">
                <span className="text-base font-bold text-blue-700">{h.label}</span>
                <span className="mt-0.5 text-xs text-gray-500">{h.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Categories grid ── */}
      <section className="bg-gray-50 py-16">
        <div className="mx-auto max-w-6xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          <div className="mb-10 flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{pageCopy.browseLabel}</span>
              <h2 className="mt-1 text-2xl font-bold text-gray-900">{pageCopy.categoriesTitle}</h2>
            </div>
            <Link
              href="/contact"
              className="hidden rounded-lg border border-blue-200 bg-white px-4 py-2 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors sm:block"
            >
              {pageCopy.contactCta}
            </Link>
          </div>

          {categories.length === 0 ? (
            <div className="flex flex-col items-center gap-4 rounded-xl border border-dashed border-gray-300 bg-white py-20 text-center text-gray-400">
              <svg className="h-14 w-14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5m6 4.125l2.25 2.25m0 0l2.25 2.25M12 13.875l2.25-2.25M12 13.875l-2.25 2.25M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z" />
              </svg>
              <p className="text-sm">{pageCopy.emptyState}</p>
              <Link href="/contact" className="text-sm font-semibold text-blue-700 hover:underline">
                {pageCopy.emptyCta}
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  href={`/products/${cat.slug}`}
                  className="group flex gap-4 rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  {getCategoryCardImage(cat) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getCategoryCardImage(cat) ?? undefined}
                      alt={cat.category_name}
                      className="h-16 w-16 flex-shrink-0 rounded-xl object-cover"
                    />
                  ) : (
                    <div className="flex h-16 w-16 flex-shrink-0 items-center justify-center rounded-xl bg-blue-50 text-3xl text-blue-600 group-hover:bg-blue-100 transition-colors">
                      ⬡
                    </div>
                  )}
                  <div className="min-w-0 flex flex-col justify-center">
                    <h2 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                      {cat.category_name}
                    </h2>
                    {cat.description && (
                      <p className="mt-1 text-sm text-gray-500 line-clamp-2">{cat.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
                    )}
                    <span className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-blue-700">
                      {pageCopy.viewProducts}
                      <svg className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                      </svg>
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* ── CTA strip ── */}
      <section className="border-t border-gray-100 bg-white py-14">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-col items-center justify-between gap-6 rounded-2xl border border-blue-100 bg-blue-50 px-8 py-10 sm:flex-row">
            <div>
              <h3 className="text-lg font-bold text-gray-900">{pageCopy.customTitle}</h3>
              <p className="mt-1 text-sm text-gray-600">
                {pageCopy.customDescription}
              </p>
            </div>
            <div className="flex shrink-0 flex-col gap-2 sm:flex-row">
              <Link
                href="/rfq"
                className="rounded-lg bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                {pageCopy.customCta}
              </Link>
              <Link
                href="/contact"
                className="rounded-lg border border-gray-300 bg-white px-6 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {pageCopy.talkCta}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
