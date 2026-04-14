import { Link } from "@/i18n/navigation";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCertificationBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type Props = { params: Promise<{ locale: string; slug: string }> };

const CERT_BADGE_VERSION = "20260318a";

type CommonMessages = {
  home: string;
};

type CertificationDetailMessages = {
  certifications: string;
  issuedBy: string;
  noBadge: string;
  whyTitle: string;
  whyDescription: string;
  fallbackDescription: string;
  certificateNo: string;
  locale: string;
  issued: string;
  expires: string;
  download: string;
  askHow: string;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const certification = await getCertificationBySlug(slug, locale);
  if (!certification) return { title: "Not Found" };
  return {
    title: certification.cert_name,
    description: certification.description || certification.issuer || undefined,
  };
}

export default async function CertificationDetailPage({ params }: Props) {
  const { siteUrl: SITE_URL, isIndustrial } = await getRuntimeSiteContext();
  const { locale, slug } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<CertificationDetailMessages>("certificationDetail"),
  ]);
  const certification = await getCertificationBySlug(slug, locale);
  if (!certification) notFound();
  const badgeImageSrc = certification.badge_image_url
    ? `${certification.badge_image_url}?v=${CERT_BADGE_VERSION}`
    : null;
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [certification]);

  if (isIndustrial) {
    return (
      <>
        <PageViewTracker pageType="certification" pageId={certification.id} />
        <StructuredData data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.certifications, url: `${SITE_URL}/certifications` },
          { name: certification.cert_name, url: `${SITE_URL}/certifications/${slug}` },
        ])} />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: copy.certifications, href: "/certifications" },
              { label: certification.cert_name },
            ]}
            eyebrow="Certification"
            title={certification.cert_name}
            description={certification.issuer ? `${copy.issuedBy} ${certification.issuer}` : undefined}
          />
          <section className="py-16">
            <div className="mx-auto grid max-w-6xl gap-8 px-6 lg:grid-cols-[260px,1fr]">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="lg:col-span-2" />}
              <div className="flex items-center justify-center border border-gray-300 bg-white p-6">
                {badgeImageSrc ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={badgeImageSrc} alt={certification.cert_name} className="max-h-36 object-contain" />
                ) : (
                  <div className="text-sm text-gray-400">{copy.noBadge}</div>
                )}
              </div>
              <div>
                <div className="mb-6 border-l-4 border-primary bg-gray-50 p-5">
                  <h2 className="text-base font-black uppercase tracking-wide text-gray-900">{copy.whyTitle}</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{copy.whyDescription}</p>
                </div>
                <div className="text-sm leading-relaxed text-gray-700 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4" dangerouslySetInnerHTML={{ __html: certification.description || copy.fallbackDescription }} />
                <dl className="mt-6 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
                  <div className="border border-gray-300 bg-white px-4 py-3"><dt className="text-gray-500">{copy.certificateNo}</dt><dd className="font-medium text-gray-700">{certification.cert_number || "—"}</dd></div>
                  <div className="border border-gray-300 bg-white px-4 py-3"><dt className="text-gray-500">{copy.locale}</dt><dd className="font-medium text-gray-700">{certification.locale}</dd></div>
                  <div className="border border-gray-300 bg-white px-4 py-3"><dt className="text-gray-500">{copy.issued}</dt><dd className="font-medium text-gray-700">{certification.issued_at ? new Date(certification.issued_at).toLocaleDateString() : "—"}</dd></div>
                  <div className="border border-gray-300 bg-white px-4 py-3"><dt className="text-gray-500">{copy.expires}</dt><dd className="font-medium text-gray-700">{certification.expires_at ? new Date(certification.expires_at).toLocaleDateString() : "—"}</dd></div>
                </dl>
                <div className="mt-6 flex flex-wrap gap-4">
                  {certification.document_url && (
                    <a href={certification.document_url} target="_blank" rel="noopener noreferrer" className="bg-primary px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-primary-foreground skew-x-[-3deg]">
                      <span className="block skew-x-[3deg]">{copy.download}</span>
                    </a>
                  )}
                  <Link href="/contact" className="border border-gray-300 px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-gray-700 hover:border-primary hover:text-primary">{copy.askHow}</Link>
                </div>
              </div>
            </div>
          </section>
        </main>
      </>
    );
  }

  return (
    <>
      <PageViewTracker pageType="certification" pageId={certification.id} />
      <StructuredData data={buildBreadcrumbSchema([
        { name: common.home, url: SITE_URL },
        { name: copy.certifications, url: `${SITE_URL}/certifications` },
        { name: certification.cert_name, url: `${SITE_URL}/certifications/${slug}` },
      ])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/certifications" className="hover:underline">{copy.certifications}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{certification.cert_name}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{certification.cert_name}</h1>
          {certification.issuer && <p className="mt-2 text-gray-500">{copy.issuedBy} {certification.issuer}</p>}
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-4xl px-6 grid gap-8 lg:grid-cols-[220px,1fr]">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="lg:col-span-2" />}
          <div className="rounded-xl border border-gray-200 bg-white p-6 flex items-center justify-center">
            {badgeImageSrc ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={badgeImageSrc} alt={certification.cert_name} className="max-h-36 object-contain" />
            ) : (
              <div className="text-sm text-gray-400">{copy.noBadge}</div>
            )}
          </div>
          <div>
            <div className="mb-6 rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h2 className="text-base font-semibold text-blue-900">{copy.whyTitle}</h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-800">
                {copy.whyDescription}
              </p>
            </div>
            <div
              className="text-gray-700 text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4"
              dangerouslySetInnerHTML={{ __html: certification.description || copy.fallbackDescription }}
            />
            <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">{copy.certificateNo}</dt><dd className="font-medium text-gray-700">{certification.cert_number || "—"}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">{copy.locale}</dt><dd className="font-medium text-gray-700">{certification.locale}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">{copy.issued}</dt><dd className="font-medium text-gray-700">{certification.issued_at ? new Date(certification.issued_at).toLocaleDateString() : "—"}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">{copy.expires}</dt><dd className="font-medium text-gray-700">{certification.expires_at ? new Date(certification.expires_at).toLocaleDateString() : "—"}</dd></div>
            </dl>
            {certification.document_url && (
              <a href={certification.document_url} target="_blank" rel="noopener noreferrer" className="mt-6 inline-block rounded-lg bg-blue-700 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                {copy.download}
              </a>
            )}
            <div className="mt-6">
              <Link href="/contact" className="text-sm font-semibold text-blue-700 hover:underline">
                {copy.askHow}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}