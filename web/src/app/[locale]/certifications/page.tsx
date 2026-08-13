import type { Metadata } from "next";
import { getPublishedCertifications } from "@/lib/api";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialCtaPanel, IndustrialPageHero } from "@/components/themes";

type CommonMessages = {
  home: string;
};

type CertificationsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  emptyState: string;
  overviewTitle: string;
  overviewDescription: string;
  items: Array<{
    type: string;
    detail: string;
    note: string;
    color: string;
    badge: string;
  }>;
  availabilityNote: string;
  availabilityCta: string;
  commitmentTitle: string;
  commitmentDescription: string;
  commitmentCta: string;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<CertificationsPageMessages>("certifications").then((copy) => copy.metadata);
}

export default async function CertificationsPage({ params }: Props) {
  const { siteUrl: SITE_URL, isIndustrial } = await getRuntimeSiteContext();
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const certifications = await getPublishedCertifications(resolvedLocale);
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<CertificationsPageMessages>("certifications"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, certifications);

  if (isIndustrial) {
    return (
      <>
        <PageViewTracker pageType="certification" />
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: pageCopy.breadcrumb, url: `${SITE_URL}/certifications` },
          ])}
        />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: pageCopy.breadcrumb },
            ]}
            eyebrow="Compliance"
            title={pageCopy.title}
            description={pageCopy.description}
          />
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
              {certifications.length === 0 ? (
                <p className="border border-dashed border-gray-300 bg-gray-50 py-16 text-center text-sm text-gray-500">{pageCopy.emptyState}</p>
              ) : (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  {certifications.map((cert) => (
                    <CertificationBadge key={cert.id} certification={cert} locale={resolvedLocale} />
                  ))}
                </div>
              )}
              <div className="mt-12 border border-gray-300 bg-white p-7">
                <h2 className="text-xl font-black uppercase tracking-wide text-gray-900">{pageCopy.overviewTitle}</h2>
                <p className="mt-2 max-w-2xl text-sm text-gray-500">{pageCopy.overviewDescription}</p>
                <div className="mt-5 grid gap-4 sm:grid-cols-3">
                  {pageCopy.items.map((item) => (
                    <div key={item.type} className="border-l-4 border-primary bg-gray-50 p-5">
                      <h3 className="text-sm font-black uppercase tracking-wide text-gray-900">{item.type}</h3>
                      <p className="mt-2 text-xs leading-relaxed text-gray-600">{item.detail}</p>
                      <span className="mt-3 inline-block bg-primary px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-primary-foreground">
                        {item.note}
                      </span>
                    </div>
                  ))}
                </div>
                <p className="mt-5 text-sm text-gray-500">
                  {pageCopy.availabilityNote}{" "}
                  <Link href="/contact" className="font-bold text-primary hover:underline">
                    {pageCopy.availabilityCta}
                  </Link>
                </p>
              </div>
              <div className="mt-12">
                <IndustrialCtaPanel
                  title={pageCopy.commitmentTitle}
                  description={pageCopy.commitmentDescription}
                  primaryHref="/contact"
                  primaryLabel={pageCopy.commitmentCta}
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
      <PageViewTracker pageType="certification" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: pageCopy.breadcrumb, url: `${SITE_URL}/certifications` },
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

      {/* Certificates grid */}
      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          {certifications.length === 0 ? (
            <p className="text-center text-gray-500 py-16">
              {pageCopy.emptyState}
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} locale={resolvedLocale} />
              ))}
            </div>
          )}

          {/* Documentation availability breakdown */}
          <div className="mt-12 rounded-2xl border border-gray-200 bg-white p-7">
            <h2 className="text-lg font-semibold text-gray-900">{pageCopy.overviewTitle}</h2>
            <p className="mt-1 text-sm text-gray-500 max-w-2xl">
              {pageCopy.overviewDescription}
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {pageCopy.items.map((item) => (
                <div key={item.type} className={`rounded-xl border p-5 ${item.color}`}>
                  <h3 className="text-sm font-semibold text-gray-800">{item.type}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-gray-600">{item.detail}</p>
                  <span className={`mt-3 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${item.badge}`}>
                    {item.note}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-5 text-sm text-gray-500">
              {pageCopy.availabilityNote}{" "}
              <Link href="/contact" className="font-medium text-blue-600 hover:underline">
                {pageCopy.availabilityCta}
              </Link>
            </p>
          </div>
        </div>
      </section>

      {/* Quality commitment section */}
      <section className="bg-blue-50 border-t border-blue-100 py-14">
        <div className="container mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-bold text-gray-800">{pageCopy.commitmentTitle}</h2>
          <p className="mt-4 text-gray-600 leading-relaxed">
            {pageCopy.commitmentDescription}
          </p>
          <Link
            href="/contact"
            className="mt-8 inline-block rounded-lg bg-blue-700 px-8 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
          >
            {pageCopy.commitmentCta}
          </Link>
        </div>
      </section>
    </>
  );
}
