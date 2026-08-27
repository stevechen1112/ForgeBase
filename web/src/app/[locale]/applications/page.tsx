import type { Metadata } from "next";
import { getPublishedApplications } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages.server";
import { resolveLocale } from "@/lib/siteCopy";
import { LocaleFallbackNotice, hasLocaleFallback } from "@/components/ui/LocaleFallbackNotice";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";
import { buildLocalizedMetadata } from "@/lib/seo";

type CommonMessages = {
  home: string;
};

type ApplicationsPageMessages = {
  metadata: Metadata;
  breadcrumb: string;
  title: string;
  description: string;
  emptyState: string;
  fallbackIndustry: string;
};

interface Props {
  params: Promise<{ locale: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const [{ siteConfig }, copy] = await Promise.all([getRuntimeSiteContext(), getMessageNamespace<ApplicationsPageMessages>("applications")]);
  return buildLocalizedMetadata(copy.metadata, "/applications", resolvedLocale, siteConfig);
}

export default async function ApplicationsPage({ params }: Props) {
  const { siteUrl: SITE_URL, isIndustrial, siteConfig: runtimeSiteConfig } = await getRuntimeSiteContext();
  const { locale } = await params;
  const resolvedLocale = resolveLocale(locale);
  const res = await getPublishedApplications(resolvedLocale, 1, 50);
  const applications = res.data;
  const [pageCopy, common] = await Promise.all([
    getMessageNamespace<ApplicationsPageMessages>("applications"),
    getMessageNamespace<CommonMessages>("common"),
  ]);
  const showLocaleFallback = hasLocaleFallback(resolvedLocale, applications);

  // Group by industry
  const byIndustry = applications.reduce<Record<string, typeof applications>>(
    (acc, app) => {
      const key = app.industry || pageCopy.fallbackIndustry;
      if (!acc[key]) acc[key] = [];
      acc[key].push(app);
      return acc;
    },
    {}
  );

  if (isIndustrial) {
    return (
      <>
        <ChatWidget contextPage="/applications" contextEntityType="application" />
        <StructuredData
          data={buildBreadcrumbSchema([
            { name: common.home, url: SITE_URL },
            { name: pageCopy.breadcrumb, url: `${SITE_URL}/applications` },
          ])}
        />
        <main className="bg-white">
          <IndustrialPageHero
            items={[
              { label: common.home, href: "/" },
              { label: pageCopy.breadcrumb },
            ]}
            eyebrow="Applications"
            title={pageCopy.title}
            description={pageCopy.description}
          />
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
              {applications.length === 0 ? (
                <p className="border border-dashed border-gray-300 bg-gray-50 py-16 text-center text-sm text-gray-500">{pageCopy.emptyState}</p>
              ) : Object.keys(byIndustry).length > 1 ? (
                Object.entries(byIndustry).map(([industry, apps]) => (
                  <div key={industry} className="mb-12 last:mb-0">
                    <div className="mb-5 flex items-center gap-3">
                      <div className="h-6 w-1.5 bg-primary" />
                      <h2 className="text-sm font-black uppercase tracking-[0.18em] text-gray-900">{industry}</h2>
                    </div>
                    <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                      {apps.map((app) => (
                        <ApplicationCard key={app.id} application={app} siteConfig={runtimeSiteConfig} locale={resolvedLocale} />
                      ))}
                    </div>
                  </div>
                ))
              ) : (
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {applications.map((app) => (
                    <ApplicationCard key={app.id} application={app} siteConfig={runtimeSiteConfig} locale={resolvedLocale} />
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
      <ChatWidget contextPage="/applications" contextEntityType="application" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: common.home, url: SITE_URL },
          { name: pageCopy.breadcrumb, url: `${SITE_URL}/applications` },
        ])}
      />

      {/* Page header */}
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

      {/* Content */}
      <section className="py-12">
        <div className="container mx-auto max-w-5xl px-6">
          {showLocaleFallback && <LocaleFallbackNotice locale={resolvedLocale} className="mb-8" />}
          {applications.length === 0 ? (
            <p className="text-center text-gray-500 py-16">{pageCopy.emptyState}</p>
          ) : Object.keys(byIndustry).length > 1 ? (
            // Multi-industry grouped view
            Object.entries(byIndustry).map(([industry, apps]) => (
              <div key={industry} className="mb-12">
                <h2 className="text-lg font-semibold text-gray-700 mb-4 border-b border-gray-100 pb-2">
                  {industry}
                </h2>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {apps.map((app) => (
                    <ApplicationCard key={app.id} application={app} siteConfig={runtimeSiteConfig} locale={resolvedLocale} />
                  ))}
                </div>
              </div>
            ))
          ) : (
            // Single industry or mixed — flat grid
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} siteConfig={runtimeSiteConfig} locale={resolvedLocale} />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
