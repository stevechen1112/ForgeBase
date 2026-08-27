import type { Metadata } from "next";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { ContactForm } from "@/components/forms/ContactForm";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { Link } from "@/i18n/navigation";
import { getPublishedPageByType } from "@/lib/api";
import { getMessageNamespace } from "@/lib/messages.server";
import { resolveLocale } from "@/lib/siteCopy";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type CommonMessages = {
  home: string;
};

type ContactPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  reasonsTitle: string;
  reasons: Array<{ label: string; desc: string }>;
  officesTitle: string;
  offices: Array<{ city: string; address: string; phone: string; hours: string }>;
  responseTitle: string;
  responseDescription: string;
  formTitle: string;
  formDescription: string;
  quickLinksPrompt: string;
  quickLinks: {
    products: string;
    certifications: string;
    rfq: string;
  };
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const { siteConfig } = await getRuntimeSiteContext();
  const pageOverride = await getPublishedPageByType("contact", resolvedLocale);
  if (pageOverride && !siteConfig.demoCompanyFolder) {
    return {
      title: pageOverride.seo_title ?? pageOverride.title,
      description: pageOverride.seo_description ?? pageOverride.subtitle ?? undefined,
    };
  }
  return getMessageNamespace<ContactPageMessages>("contactPage").then((copy) => copy.metadata);
}

export default async function ContactPage({ params }: Props) {
  const {
    siteUrl: SITE_URL,
    siteName: SITE_NAME,
    contactEmail,
    contactPhone,
    isIndustrial,
    siteConfig,
  } = await getRuntimeSiteContext();
  const { locale } = await params;
  resolveLocale(locale);
  // Seeded CMS contact pages are sparse FlexiblePage bodies; use the assembled Contact page instead.
  const [copy, common] = await Promise.all([
    getMessageNamespace<ContactPageMessages>("contactPage"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const isTestScenario = Boolean(siteConfig.demoCompanyFolder);
  if (isIndustrial) {
    return (
      <>
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: copy.breadcrumb, url: `${SITE_URL}/contact` },
          ])}
        />
        <PageViewTracker pageType="contact" />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: copy.breadcrumb },
            ]}
            eyebrow={isTestScenario ? "ForgeBase functional test" : "Sales Contact"}
            title={copy.title || SITE_NAME}
            description={copy.description}
          >
            {!isTestScenario && <div className="flex flex-wrap gap-3">
              <a href={`mailto:${contactEmail}`} className="border border-gray-700 px-4 py-2 text-[11px] font-black uppercase tracking-[0.16em] text-gray-300 hover:border-primary hover:text-primary">
                {contactEmail}
              </a>
              <a href={`tel:${contactPhone.replace(/\D/g, "")}`} className="border border-gray-700 px-4 py-2 text-[11px] font-black uppercase tracking-[0.16em] text-gray-300 hover:border-primary hover:text-primary">
                {contactPhone}
              </a>
            </div>}
          </IndustrialPageHero>
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              <div className="grid gap-10 lg:grid-cols-5">
                <div className="space-y-8 lg:col-span-2">
                  <div>
                    <h2 className="text-lg font-black uppercase tracking-wide text-gray-900">{copy.reasonsTitle}</h2>
                    <ul className="mt-4 space-y-3">
                      {copy.reasons.map((r) => (
                        <li key={r.label} className="border-l-4 border-primary bg-gray-50 p-4">
                          <p className="text-sm font-black uppercase tracking-wide text-gray-900">{r.label}</p>
                          <p className="mt-1 text-xs leading-relaxed text-gray-500">{r.desc}</p>
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <h2 className="text-lg font-black uppercase tracking-wide text-gray-900">{copy.officesTitle}</h2>
                    <div className="mt-4 space-y-4">
                      {copy.offices.map((office) => (
                        <div key={office.city} className="border border-gray-300 bg-white p-4">
                          <h3 className="text-sm font-black uppercase tracking-wide text-primary">{office.city}</h3>
                          <dl className="mt-3 space-y-2 text-sm text-gray-600">
                            <div>{office.address}</div>
                            <div>{office.phone}</div>
                            <div>{office.hours}</div>
                          </dl>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="border-l-4 border-primary bg-gray-50 p-4">
                    <span className="text-sm font-black uppercase tracking-wide text-gray-900">{copy.responseTitle}</span>
                    <p className="mt-2 text-xs leading-relaxed text-gray-600">{copy.responseDescription}</p>
                  </div>
                </div>
                <div className="lg:col-span-3">
                  <div className="border border-gray-300 bg-white p-8">
                    <h2 className="mb-1 text-xl font-black uppercase tracking-wide text-gray-900">{copy.formTitle}</h2>
                    <p className="mb-6 text-sm text-gray-500">{copy.formDescription}</p>
                    <ContactForm />
                  </div>
                </div>
              </div>
            </div>
          </section>
          <section className="border-t border-gray-200 bg-gray-50 py-12">
            <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6">
              <p className="text-sm font-bold uppercase tracking-wide text-gray-700">{copy.quickLinksPrompt}</p>
              <div className="flex flex-wrap gap-3">
                <Link href="/products" className="border border-gray-300 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-gray-800 hover:border-primary hover:text-primary">{copy.quickLinks.products}</Link>
                <Link href="/certifications" className="border border-gray-300 px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-gray-800 hover:border-primary hover:text-primary">{copy.quickLinks.certifications}</Link>
                <Link href="/rfq" className="bg-primary px-4 py-2 text-sm font-black uppercase tracking-[0.16em] text-primary-foreground">{copy.quickLinks.rfq}</Link>
              </div>
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
          { name: copy.breadcrumb, url: `${SITE_URL}/contact` },
        ])}
      />
      <PageViewTracker pageType="contact" />

      {/* ── Hero header ── */}
      <section className="border-b border-gray-100 bg-gradient-to-br from-blue-950 to-blue-800 py-16 text-white">
        <div className="mx-auto max-w-6xl px-6">
          <nav aria-label="Breadcrumb" className="mb-4 text-xs text-blue-300">
            <Link href="/" className="hover:underline">{common.home}</Link>
            <span className="mx-1.5">/</span>
            <span>{copy.breadcrumb}</span>
          </nav>
          <h1 className="text-4xl font-extrabold">{copy.title || SITE_NAME}</h1>
          <p className="mt-3 max-w-xl text-lg text-blue-200 leading-relaxed">
            {copy.description}
          </p>

          {/* Quick contact chips */}
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={`mailto:${contactEmail}`}
              className="flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-2 text-sm text-blue-100 hover:bg-blue-700/50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              {contactEmail}
            </a>
            <a
              href={`tel:${contactPhone.replace(/\D/g, "")}`}
              className="flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-2 text-sm text-blue-100 hover:bg-blue-700/50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              {contactPhone}
            </a>
          </div>
        </div>
      </section>

      {/* ── Main content ── */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-5">

            {/* Left column (info) */}
            <div className="lg:col-span-2 space-y-8">

              {/* Why contact us */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{copy.reasonsTitle}</h2>
                <ul className="mt-4 space-y-3">
                  {copy.reasons.map((r) => (
                    <li key={r.label} className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{r.label}</p>
                        <p className="text-xs text-gray-500">{r.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Offices */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">{copy.officesTitle}</h2>
                <div className="mt-4 space-y-4">
                  {copy.offices.map((office) => (
                    <div key={office.city} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h3 className="text-sm font-bold text-blue-700">{office.city}</h3>
                      <dl className="mt-2 space-y-1 text-sm text-gray-600">
                        <div className="flex items-start gap-2">
                          <svg className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                          </svg>
                          <span>{office.address}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                          </svg>
                          <span>{office.phone}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>{office.hours}</span>
                        </div>
                      </dl>
                    </div>
                  ))}
                </div>
              </div>

              {/* Response promise */}
              <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
                <div className="flex items-center gap-2">
                  <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-semibold text-blue-800">{copy.responseTitle}</span>
                </div>
                <p className="mt-2 text-xs text-blue-700 leading-relaxed">
                  {copy.responseDescription}
                </p>
              </div>

            </div>

            {/* Right column (form) */}
            <div className="lg:col-span-3">
              <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
                <h2 className="mb-1 text-xl font-bold text-gray-900">{copy.formTitle}</h2>
                <p className="mb-6 text-sm text-gray-500">
                  {copy.formDescription}
                </p>
                <ContactForm />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── Quick links ── */}
      <section className="border-t border-gray-100 bg-gray-50 py-12">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm font-medium text-gray-700">
              {copy.quickLinksPrompt}
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/products" className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors">
                {copy.quickLinks.products}
              </Link>
              <Link href="/certifications" className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors">
                {copy.quickLinks.certifications}
              </Link>
              <Link href="/rfq" className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                {copy.quickLinks.rfq}
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}
