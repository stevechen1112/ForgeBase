import { Link } from "@/i18n/navigation";
import type { Metadata } from "next";
import { getPublishedCapabilities, getPublishedCertifications } from "@/lib/api";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildBreadcrumbSchema, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { ABOUT_HERO_IMAGE } from "@/lib/demoAssets";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { siteConfig } from "@/lib/siteConfig";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";

interface Props {
  params: Promise<{ locale: string }>;
}

const SITE_URL = siteConfig.siteUrl;
const SITE_NAME = siteConfig.brandName;

type CommonMessages = {
  home: string;
};

type AboutMessages = {
  metadata: Metadata;
  breadcrumb: string;
  heroTitle: string;
  heroDescription: string;
  stats: Array<{ value: string; label: string }>;
  ourStory: string;
  storyTitle: string;
  talkTeam: string;
  whatWeMake: string;
  productLinesTitle: string;
  ourJourney: string;
  milestones: string;
  strengthsEyebrow: string;
  strengthsTitle: string;
  capabilitiesEyebrow: string;
  capabilitiesTitle: string;
  certificationsEyebrow: string;
  certificationsTitle: string;
  ctaTitle: string;
  ctaDescription: string;
  contactTeam: string;
  browseProducts: string;
  productLines: Array<{ title: string; desc: string }>;
  timeline: Array<{ year: string; event: string }>;
  operationalStrengths: Array<{ title: string; desc: string }>;
  storyParagraphs: string[];
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  resolveLocale(locale);
  return getMessageNamespace<AboutMessages>("about").then((copy) => copy.metadata);
}

export default async function AboutPage({ params }: Props) {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [common, copy] = await Promise.all([
    getMessageNamespace<CommonMessages>("common"),
    getMessageNamespace<AboutMessages>("about"),
  ]);
  const [capabilities, certifications] = await Promise.all([
    getPublishedCapabilities(locale),
    getPublishedCertifications(locale),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, [...capabilities, ...certifications]);

  return (
    <>
      <PageViewTracker pageType="about" />
      <StructuredData
        data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
      />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: copy.breadcrumb, url: `${SITE_URL}/about` },
        ])}
      />

      {/* ── Hero header ── */}
      <section className="relative overflow-hidden border-b border-gray-100 py-16 text-white">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${ABOUT_HERO_IMAGE})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/85 via-blue-950/78 to-blue-900/50" />
        <div className="mx-auto max-w-6xl px-6">
          <nav aria-label="Breadcrumb" className="relative mb-4 text-xs text-blue-300">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1.5">/</span>
            <span>{copy.breadcrumb}</span>
          </nav>
          <h1 className="relative text-4xl font-extrabold">{copy.heroTitle}</h1>
          <p className="relative mt-3 max-w-2xl text-lg text-blue-200 leading-relaxed">
            {copy.heroDescription}
          </p>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-2 divide-x divide-y divide-gray-100 sm:grid-cols-4 sm:divide-y-0">
            {copy.stats.map((s) => (
              <div key={s.label} className="flex flex-col items-center py-8 text-center">
                <span className="text-3xl font-extrabold text-blue-700">{s.value}</span>
                <span className="mt-1 text-sm text-gray-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Company story ── */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.ourStory}</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.storyTitle}</h2>
              {copy.storyParagraphs.map((paragraph) => (
                <p key={paragraph} className="mt-4 leading-relaxed text-gray-600">
                  {paragraph}
                </p>
              ))}
              <Link
                href="/contact"
                className="mt-8 inline-flex items-center gap-2 rounded-lg bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                {copy.talkTeam}
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>

            {/* Factory illustration placeholder */}
            <div className="overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={ABOUT_HERO_IMAGE}
                alt={`${SITE_NAME} factory and manufacturing environment`}
                className="aspect-video w-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Core values ── */}
      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.whatWeMake}</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.productLinesTitle}</h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {copy.productLines.map((v) => (
              <div key={v.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mt-4 text-base font-semibold text-gray-900">{v.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Timeline ── */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.ourJourney}</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.milestones}</h2>
          </div>
          <div className="relative mt-12 ml-4 border-l-2 border-blue-200 pl-8 sm:ml-24 space-y-8">
            {copy.timeline.map((item) => (
              <div key={item.year} className="relative">
                {/* Dot */}
                <div className="absolute -left-[2.6rem] flex h-5 w-5 items-center justify-center rounded-full border-2 border-blue-400 bg-white">
                  <div className="h-2 w-2 rounded-full bg-blue-500" />
                </div>
                <span className="text-xs font-bold uppercase tracking-widest text-blue-600">{item.year}</span>
                <p className="mt-1 text-sm leading-relaxed text-gray-700">{item.event}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Leadership team ── */}
      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.strengthsEyebrow}</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.strengthsTitle}</h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {copy.operationalStrengths.map((item) => (
              <div key={item.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Capabilities ── */}
      {capabilities.length > 0 && (
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.capabilitiesEyebrow}</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.capabilitiesTitle}</h2>
            </div>
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {capabilities.map((cap) => (
                <Link
                  key={cap.id}
                  href={`/capabilities/${cap.slug}`}
                  className="flex flex-col rounded-xl border border-gray-100 bg-gray-50 p-6 shadow-sm hover:border-blue-200 hover:shadow-md transition-all"
                >
                  {cap.icon_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={cap.icon_url} alt="" className="mb-3 h-10 w-10 object-contain" aria-hidden="true" />
                  ) : (
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-base font-bold text-blue-700">
                      {cap.capability_name.charAt(0)}
                    </div>
                  )}
                  <h3 className="font-semibold text-gray-900">{cap.capability_name}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-gray-500">{cap.short_description}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">{copy.certificationsEyebrow}</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">{copy.certificationsTitle}</h2>
            </div>
            <div className="mt-12 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── CTA ── */}
      <section className="bg-blue-900 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold">{copy.ctaTitle}</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            {copy.ctaDescription}
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/contact"
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              {copy.contactTeam}
            </Link>
            <Link
              href="/products"
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              {copy.browseProducts}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
