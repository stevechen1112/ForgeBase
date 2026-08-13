/**
 * RFQ Page — 1b.4.1
 * /rfq
 *
 * Static page with trust elements + RFQForm client component.
 * noindex by default (private B2B conversion page).
 */
import type { Metadata } from "next";
import { RFQForm } from "@/components/forms/RFQForm";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { Link } from "@/i18n/navigation";
import { getMessageNamespace } from "@/lib/messages";
import { resolveLocale } from "@/lib/siteCopy";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";
import { IndustrialPageHero } from "@/components/themes";

type RFQPageMessages = {
  metadata: {
    title: string;
    description: string;
  };
  title: string;
  description: string;
  builtForTitle: string;
  builtForItems: string[];
  helpTitle: string;
  helpDescription: string;
  helpCta: string;
  responseWindowLabel: string;
  responseWindowTime: string;
  responseWindowHours: string;
};

interface Props {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{
    product_id?: string;
    product_ids?: string;
    application_id?: string;
    quantity?: string;
    specifications?: string;
    message?: string;
    requirement_summary?: string;
  }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { siteName: BRAND } = await getRuntimeSiteContext();
  await params;
  const copy = await getMessageNamespace<RFQPageMessages>("rfqPage");
  return {
    title: `${copy.metadata.title} - ${BRAND}`,
    description: copy.metadata.description,
    robots: { index: false, follow: false },
  };
}

export default async function RFQPage({ params, searchParams }: Props) {
  const { isIndustrial } = await getRuntimeSiteContext();
  const { locale } = await params;
  resolveLocale(locale);
  const copy = await getMessageNamespace<RFQPageMessages>("rfqPage");
  const sp = await searchParams;
  const productIds = (sp.product_ids || sp.product_id || "")
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean)
    .slice(0, 10);
  const applicationId = sp.application_id;

  if (isIndustrial) {
    return (
      <>
        <PageViewTracker pageType="rfq" />
        <main className="min-h-screen bg-white">
          <IndustrialPageHero
            items={[{ label: copy.metadata.title.includes("詢價") ? "首頁" : "Home", href: "/" }, { label: "RFQ" }]}
            eyebrow={copy.metadata.title.includes("詢價") ? "詢價" : "Quotation"}
            title={copy.title}
            description={copy.description}
          />
          <section className="py-16">
            <div className="mx-auto max-w-7xl px-6">
              <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
                <aside className="space-y-6 lg:col-span-1">
                  <div className="border border-gray-300 bg-white p-5">
                    <h2 className="mb-4 text-base font-black uppercase tracking-wide text-gray-900">{copy.builtForTitle}</h2>
                    <ul className="space-y-3 text-sm text-gray-600">
                      {copy.builtForItems.map((item) => (
                        <li key={item} className="border-l-4 border-primary bg-gray-50 px-3 py-2">{item}</li>
                      ))}
                    </ul>
                  </div>
                  <div className="border-l-4 border-primary bg-gray-50 p-5">
                    <h2 className="mb-2 text-base font-black uppercase tracking-wide text-gray-900">{copy.helpTitle}</h2>
                    <p className="mb-3 text-sm leading-relaxed text-gray-600">{copy.helpDescription}</p>
                    <Link href="/contact" className="text-[11px] font-black uppercase tracking-[0.16em] text-primary hover:underline">
                      {copy.helpCta}
                    </Link>
                  </div>
                  <div className="border border-gray-300 bg-gray-900 p-5 text-center text-white">
                    <div className="text-3xl font-black text-primary">{copy.responseWindowTime}</div>
                    <div className="mt-1 text-xs font-black uppercase tracking-[0.16em] text-gray-300">{copy.responseWindowLabel}</div>
                    <div className="mt-2 text-xs text-gray-500">{copy.responseWindowHours}</div>
                  </div>
                </aside>
                <div className="lg:col-span-2 border border-gray-300 bg-white p-6">
                  <RFQForm
                    preselectedProductIds={productIds}
                    preselectedApplicationId={applicationId}
                  />
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
      <PageViewTracker pageType="rfq" />
      <main className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="mx-auto max-w-5xl">
          {/* Header */}
          <div className="mb-10 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-3">
              {copy.title}
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              {copy.description}
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Trust sidebar */}
            <aside className="lg:col-span-1 space-y-6">
              <div className="rounded-lg bg-white border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-800 mb-4">{copy.builtForTitle}</h2>
                <ul className="space-y-3 text-sm text-gray-600">
                  {copy.builtForItems.map((item) => (
                    <li key={item} className="flex items-start gap-2">
                      <svg className="mt-0.5 h-4 w-4 flex-shrink-0 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                      {item}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-lg bg-blue-50 border border-blue-200 p-5">
                <h2 className="font-semibold text-blue-800 mb-2">{copy.helpTitle}</h2>
                <p className="text-sm text-blue-700 mb-3">
                  {copy.helpDescription}
                </p>
                <Link
                  href="/contact"
                  className="text-sm font-medium text-blue-600 underline hover:text-blue-800"
                >
                  {copy.helpCta}
                </Link>
              </div>

              {/* Response time guarantee */}
              <div className="rounded-lg bg-green-50 border border-green-200 p-5 text-center">
                <div className="text-2xl font-bold text-green-700">{copy.responseWindowTime}</div>
                <div className="text-sm text-green-600 mt-1">{copy.responseWindowLabel}</div>
                <div className="text-xs text-green-500 mt-2">
                  {copy.responseWindowHours}
                </div>
              </div>
            </aside>

            {/* Form */}
            <div className="lg:col-span-2 rounded-lg bg-white border border-gray-200 p-6 shadow-sm">
              <RFQForm
                preselectedProductIds={productIds}
                preselectedApplicationId={applicationId}
              />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
