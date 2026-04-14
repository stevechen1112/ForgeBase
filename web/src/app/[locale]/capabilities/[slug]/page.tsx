import { Link } from "@/i18n/navigation";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCapabilityBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type Props = { params: Promise<{ locale: string; slug: string }> };

type CommonMessages = {
  home: string;
};

type CapabilityDetailMessages = {
  capabilities: string;
  commercialBenefit: string;
  commercialBenefitDescription: string;
  snapshot: string;
  focusArea: string;
  relevantAt: string;
  appliesTo: string;
  general: string;
  relevantValue: string;
  appliesValue: string;
  discussionDescription: string;
  discuss: string;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale, slug } = await params;
  const capability = await getCapabilityBySlug(slug, locale);
  if (!capability) return { title: "Not Found" };
  return {
    title: capability.capability_name,
    description: capability.short_description,
  };
}

export default async function CapabilityDetailPage({ params }: Props) {
  const { siteUrl: SITE_URL, isIndustrial } = await getRuntimeSiteContext();
  const { locale, slug } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<CapabilityDetailMessages>("capabilityDetail"),
  ]);
  const capability = await getCapabilityBySlug(slug, locale);
  if (!capability) notFound();
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [capability]);

  if (isIndustrial) {
    return (
      <>
        <PageViewTracker pageType="capability" pageId={capability.id} />
        <StructuredData data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.capabilities, url: `${SITE_URL}/capabilities` },
          { name: capability.capability_name, url: `${SITE_URL}/capabilities/${capability.slug}` },
        ])} />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: copy.capabilities, href: "/capabilities" },
              { label: capability.capability_name },
            ]}
            eyebrow={capability.category_tag || copy.capabilities}
            title={capability.capability_name}
            description={capability.short_description}
          />
          <section className="py-16">
            <div className="mx-auto grid max-w-6xl gap-8 px-6 lg:grid-cols-2">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="lg:col-span-2" />}
              <div>
                <div className="mb-6 border-l-4 border-primary bg-gray-50 p-5">
                  <h2 className="text-base font-black uppercase tracking-wide text-gray-900">{copy.commercialBenefit}</h2>
                  <p className="mt-2 text-sm leading-relaxed text-gray-600">{copy.commercialBenefitDescription}</p>
                </div>
                <div className="text-sm leading-relaxed text-gray-700 [&_ol]:list-decimal [&_ol]:pl-4 [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4" dangerouslySetInnerHTML={{ __html: capability.detail || capability.short_description }} />
              </div>
              <div className="border border-gray-300 bg-white p-6">
                <h2 className="mb-3 text-lg font-black uppercase tracking-wide text-gray-900">{copy.snapshot}</h2>
                <dl className="space-y-3 text-sm">
                  <div className="flex justify-between gap-4 border-b border-gray-200 pb-3"><dt className="text-gray-500">{copy.focusArea}</dt><dd className="font-medium text-gray-700 capitalize">{capability.category_tag || copy.general}</dd></div>
                  <div className="flex justify-between gap-4 border-b border-gray-200 pb-3"><dt className="text-gray-500">{copy.relevantAt}</dt><dd className="font-medium text-gray-700">{copy.relevantValue}</dd></div>
                  <div className="flex justify-between gap-4"><dt className="text-gray-500">{copy.appliesTo}</dt><dd className="font-medium text-gray-700">{copy.appliesValue}</dd></div>
                </dl>
                <div className="mt-6 border-t border-gray-200 pt-6">
                  <p className="text-sm leading-relaxed text-gray-600">{copy.discussionDescription}</p>
                  <Link href="/contact" className="mt-4 inline-block bg-primary px-6 py-3 text-sm font-black uppercase tracking-[0.16em] text-primary-foreground skew-x-[-3deg]"><span className="block skew-x-[3deg]">{copy.discuss}</span></Link>
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
      <PageViewTracker pageType="capability" pageId={capability.id} />
      <StructuredData data={buildBreadcrumbSchema([
        { name: common.home, url: SITE_URL },
        { name: copy.capabilities, url: `${SITE_URL}/capabilities` },
        { name: capability.capability_name, url: `${SITE_URL}/capabilities/${capability.slug}` },
      ])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1">/</span>
            <Link href="/capabilities" className="hover:underline">{copy.capabilities}</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{capability.capability_name}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{capability.capability_name}</h1>
          <p className="mt-3 text-gray-500 max-w-2xl">{capability.short_description}</p>
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6 grid gap-8 lg:grid-cols-2">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="lg:col-span-2" />}
          <div>
            <div className="mb-6 rounded-xl border border-blue-100 bg-blue-50 p-5">
              <h2 className="text-base font-semibold text-blue-900">{copy.commercialBenefit}</h2>
              <p className="mt-2 text-sm leading-relaxed text-blue-800">
                {copy.commercialBenefitDescription}
              </p>
            </div>
            <div
              className="text-gray-700 text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:list-disc [&_ul]:pl-4 [&_ol]:list-decimal [&_ol]:pl-4"
              dangerouslySetInnerHTML={{ __html: capability.detail || capability.short_description }}
            />
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">{copy.snapshot}</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">{copy.focusArea}</dt>
                <dd className="font-medium text-gray-700 capitalize">{capability.category_tag || copy.general}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">{copy.relevantAt}</dt>
                <dd className="font-medium text-gray-700">{copy.relevantValue}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-gray-500">{copy.appliesTo}</dt>
                <dd className="font-medium text-gray-700">{copy.appliesValue}</dd>
              </div>
            </dl>
            <div className="mt-6 space-y-3 border-t border-gray-200 pt-6">
              <p className="text-sm leading-relaxed text-gray-600">
                {copy.discussionDescription}
              </p>
              <Link href="/contact" className="inline-flex rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                {copy.discuss}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}