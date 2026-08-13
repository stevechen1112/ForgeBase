import Link from "next/link";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import {
  getPublishedCategories,
  getPublishedApplications,
  getPublishedCertifications,
  getFeaturedProducts,
  getPublishedPageBySlug,
  getPublishedPageByType,
} from "@/lib/api";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { FlexiblePageRenderer } from "@/components/pages/FlexiblePageRenderer";
import { StructuredData, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getCategoryCardImage, getHomeHeroImage, getProductImage } from "@/lib/demoAssets";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialHomePage } from "@/components/themes";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { localizedPath } from "@/lib/localizedPath";

function isSupportedLocale(locale: string): boolean {
  return locale === "en" || locale === "zh-TW";
}

const WHY_US_ICONS = [
  (
    <svg key="repeat-orders" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  (
    <svg key="oem-private-label" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.017-.017c.372-.372.596-.878.596-1.414 0-.523-.199-1.026-.554-1.403L9.62 5.498a1.875 1.875 0 00-2.346-.271l-1.16.58z" />
    </svg>
  ),
  (
    <svg key="documentation" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
    </svg>
  ),
  (
    <svg key="mixed-sku" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
    </svg>
  ),
  (
    <svg key="product-scope" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  (
    <svg key="compliance" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
];

type HomeMessages = {
  metadata: Metadata;
  hero: {
    eyebrow: string;
    titleLine1: string;
    titleLine2: string;
    description: string;
    primaryCta: string;
    secondaryCta: string;
  };
  stats: Array<{ value: string; label: string }>;
  featured: {
    eyebrow: string;
    title: string;
    description: string;
    cardCta: string;
    sectionCta: string;
  };
  catalogue: {
    eyebrow: string;
    title: string;
    description: string;
    sectionCta: string;
  };
  why: {
    eyebrow: string;
    title: string;
    description: string;
    items: Array<{ title: string; desc: string }>;
  };
  applications: {
    eyebrow: string;
    title: string;
    description: string;
    sectionCta: string;
  };
  oem: {
    eyebrow: string;
    title: string;
    description: string;
    steps: Array<{ title: string; desc: string }>;
  };
  certifications: {
    eyebrow: string;
    title: string;
    description: string;
    sectionCta: string;
  };
  finalCta: {
    title: string;
    description: string;
    primaryCta: string;
    secondaryCta: string;
    note: string;
  };
};

export async function generateMetadata({ params }: { params: Promise<{ locale: string }> }): Promise<Metadata> {
  const { locale } = await params;
  if (!isSupportedLocale(locale)) {
    const customPage = await getPublishedPageBySlug(locale);
    if (customPage) {
      return {
        title: customPage.seo_title ?? customPage.title,
        description: customPage.seo_description ?? customPage.subtitle ?? undefined,
      };
    }
    return {};
  }

  const resolvedLocale = resolveLocale(locale);
  const pageOverride = await getPublishedPageByType("home", resolvedLocale);
  if (pageOverride) {
    return {
      title: pageOverride.seo_title ?? pageOverride.title,
      description: pageOverride.seo_description ?? pageOverride.subtitle ?? undefined,
    };
  }
  const copy = await getMessageNamespace<HomeMessages>("home");
  return {
    title: copy.metadata.title,
    description: copy.metadata.description,
  };
}

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;

  if (!isSupportedLocale(locale)) {
    const customPage = await getPublishedPageBySlug(locale);
    if (!customPage) {
      notFound();
    }
    return <FlexiblePageRenderer page={customPage} />;
  }

  const { siteUrl: SITE_URL, siteName: SITE_NAME, isIndustrial, siteConfig: runtimeSiteConfig } = await getRuntimeSiteContext();
  const resolvedLocale = resolveLocale(locale);
  // Seeded CMS `home` pages are sparse FlexiblePage bodies. They must not replace the
  // assembled marketing homepage (featured products / categories / applications).
  const copy = await getMessageNamespace<HomeMessages>("home");
  const [categories, applicationsRes, certifications, featuredProducts] = await Promise.all([
    getPublishedCategories(resolvedLocale),
    getPublishedApplications(resolvedLocale),
    getPublishedCertifications(resolvedLocale),
    getFeaturedProducts(resolvedLocale),
  ]);
  const applications = applicationsRes.data.slice(0, 6);
  const categorySlugById = new Map(categories.map((category) => [category.id, category.slug]));
  const showLocaleFallback = hasLocaleFallback(
    resolvedLocale,
    [...categories, ...applications, ...certifications, ...featuredProducts]
  );

  // ── Industrial layout: completely different page assembly ──
  if (isIndustrial) {
    return (
      <>
        <PageViewTracker pageType="home" />
        <ChatWidget contextPage="/" contextEntityType="home" />
        <StructuredData
          data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
        />
        {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mx-auto my-6 max-w-7xl px-6" />}
        <IndustrialHomePage
          copy={copy}
          featuredProducts={featuredProducts}
          categories={categories}
          applications={applications}
          certifications={certifications}
          categorySlugById={categorySlugById}
          siteConfig={runtimeSiteConfig}
          locale={resolvedLocale}
        />
      </>
    );
  }

  return (
    <>
      <PageViewTracker pageType="home" />
      <ChatWidget contextPage="/" contextEntityType="home" />
      <StructuredData
        data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
      />
      {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mx-auto my-6 max-w-6xl px-6" />}

      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-slate-950 text-white">
        {/* Photo on the right only — generated heroes often bake fake UI into the left half */}
        <div
          className="absolute inset-y-0 right-0 hidden w-[52%] bg-cover bg-center md:block"
          style={{
            backgroundImage: `url(${getHomeHeroImage(runtimeSiteConfig)})`,
            backgroundPosition: "68% center",
          }}
        />
        <div className="absolute inset-y-0 right-0 hidden w-[52%] bg-gradient-to-l from-transparent to-slate-950 md:block" />
        <div className="relative mx-auto max-w-6xl px-6 py-28 sm:py-36">
          <div className="flex max-w-xl flex-col text-left">
            <span className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-blue-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
              {copy.hero.eyebrow}
            </span>

            <h1 className="text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              {copy.hero.titleLine1}
              <br />
              <span className="text-blue-300">{copy.hero.titleLine2}</span>
            </h1>

            <p className="mt-5 text-lg leading-relaxed text-blue-100">
              {copy.hero.description}
            </p>

            <div className="mt-9 flex flex-col gap-4 sm:flex-row">
              <Link
                href={localizedPath(resolvedLocale, "/rfq")}
                className="rounded-xl bg-white px-8 py-3.5 text-center text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
              >
                {copy.hero.primaryCta}
              </Link>
              <Link
                href={localizedPath(resolvedLocale, "/products")}
                className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-center text-sm font-semibold text-white hover:bg-white/20 transition-colors"
              >
                {copy.hero.secondaryCta}
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust bar / Stats ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {copy.stats.map((s) => (
              <div key={s.label} className="flex flex-col items-center text-center">
                <span className="text-3xl font-extrabold text-blue-700">{s.value}</span>
                <span className="mt-1 text-sm text-gray-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Featured Products ── */}
      {featuredProducts.length > 0 && (
        <section className="bg-white py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.featured.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.featured.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.featured.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {featuredProducts.map((product) => (
                <Link
                  key={product.id}
                  href={localizedPath(resolvedLocale, categorySlugById.get(product.category_id) ? `/products/${categorySlugById.get(product.category_id)}/${product.slug}` : "/products")}
                  className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="mb-3 h-32 w-full overflow-hidden rounded-lg bg-blue-50">
                    {getProductImage(product, categorySlugById.get(product.category_id), runtimeSiteConfig) ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={getProductImage(product, categorySlugById.get(product.category_id), runtimeSiteConfig) ?? undefined}
                        alt={product.product_name}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-4xl text-blue-300 group-hover:bg-blue-100 transition-colors">
                        ⬡
                      </div>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                    {product.product_name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">{product.model_number}</p>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-500">
                    {product.short_description}
                  </p>
                  <span className="mt-3 text-xs font-semibold text-blue-600 group-hover:underline">
                    {copy.featured.cardCta}
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href={localizedPath(resolvedLocale, "/products")}
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                {copy.featured.sectionCta}
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Product Categories ── */}
      {categories.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.catalogue.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.catalogue.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.catalogue.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  href={localizedPath(resolvedLocale, `/products/${cat.slug}`)}
                  className="group flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  {getCategoryCardImage(cat, runtimeSiteConfig) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getCategoryCardImage(cat, runtimeSiteConfig) ?? undefined}
                      alt={cat.category_name}
                      className="mb-3 h-20 w-full rounded-lg object-cover"
                    />
                  ) : (
                    <span className="mb-3 flex h-20 w-full items-center justify-center rounded-lg bg-blue-50 text-3xl group-hover:bg-blue-100 transition-colors">
                      ⬡
                    </span>
                  )}
                  <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                    {cat.category_name}
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href={localizedPath(resolvedLocale, "/products")}
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                {copy.catalogue.sectionCta}
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Why Choose Us ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              {copy.why.eyebrow}
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.why.title}</h2>
            <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
              {copy.why.description}
            </p>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {copy.why.items.map((item, index) => (
              <div
                key={item.title}
                className="rounded-xl border border-gray-100 bg-gray-50 p-6 hover:border-blue-200 hover:bg-blue-50/30 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                  {WHY_US_ICONS[index]}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Applications ── */}
      {applications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.applications.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.applications.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.applications.description}
              </p>
            </div>

            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} siteConfig={runtimeSiteConfig} locale={resolvedLocale} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href={localizedPath(resolvedLocale, "/applications")}
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                {copy.applications.sectionCta}
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── OEM / ODM flow ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              {copy.oem.eyebrow}
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.oem.title}</h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
              {copy.oem.description}
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {copy.oem.steps.map((step, index) => (
              <div key={step.title} className="rounded-xl border border-gray-100 bg-gray-50 p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-700 text-sm font-bold text-white">
                  0{index + 1}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                {copy.certifications.eyebrow}
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.certifications.title}</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                {copy.certifications.description}
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href={localizedPath(resolvedLocale, "/certifications")}
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                {copy.certifications.sectionCta}
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── CTA Banner ── */}
      <section className="bg-blue-900 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold">{copy.finalCta.title}</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            {copy.finalCta.description}
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href={localizedPath(resolvedLocale, "/rfq")}
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              {copy.finalCta.primaryCta}
            </Link>
            <Link
              href={localizedPath(resolvedLocale, "/contact")}
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              {copy.finalCta.secondaryCta}
            </Link>
          </div>
          <p className="mt-6 text-xs text-blue-400">
            {copy.finalCta.note}
          </p>
        </div>
      </section>
    </>
  );
}
