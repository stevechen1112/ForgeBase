/**
 * RFQ Page — 1b.4.1
 * /rfq
 *
 * Static page with trust elements + RFQForm client component.
 * noindex by default (private B2B conversion page).
 */
import type { Metadata } from "next";
import Link from "next/link";
import { RFQForm } from "@/components/forms/RFQForm";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName: BRAND } = await getRuntimeSiteContext();

  return {
    title: `Request a Quotation — ${BRAND}`,
    description: "Submit your RFQ for torque tools, insulated tools, workshop tools, or private-label toolkit programs. Get a qualified response within 1 business day.",
    robots: { index: false, follow: false },
  };
}

interface Props {
  searchParams: Promise<{ product_id?: string; application_id?: string }>;
}

export default async function RFQPage({ searchParams }: Props) {
  const { siteName: BRAND } = await getRuntimeSiteContext();
  const sp = await searchParams;
  const productIds = sp.product_id ? [sp.product_id] : [];
  const applicationId = sp.application_id;

  return (
    <>
      <PageViewTracker pageType="rfq" />
      <main className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="mx-auto max-w-5xl">
          {/* Header */}
          <div className="mb-10 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-3">
              Request a Tool Program Quotation
            </h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Share your product scope, packaging needs, and sourcing timeline.
              Our team will review the details and respond with the right next step within
              <strong> 1 business day</strong>.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Trust sidebar */}
            <aside className="lg:col-span-1 space-y-6">
              <div className="rounded-lg bg-white border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-800 mb-4">What this RFQ is built for</h2>
                <ul className="space-y-3 text-sm text-gray-600">
                  {[
                    "Standard tool sourcing and recurring distributor supply",
                    "Private-label packaging, barcode, and molded-case programs",
                    "Mixed-SKU toolkit builds and drawer-set assortments",
                    "Specification review for torque, insulation, material, and finish requirements",
                    "Documentation support for export and compliance-sensitive orders",
                    "NDA requests for confidential OEM discussions",
                  ].map((item) => (
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
                <h2 className="font-semibold text-blue-800 mb-2">Need help?</h2>
                <p className="text-sm text-blue-700 mb-3">
                  If you only know the application and target market, {BRAND} can help narrow down the right tool family and packaging path.
                </p>
                <Link
                  href="/contact"
                  className="text-sm font-medium text-blue-600 underline hover:text-blue-800"
                >
                  Contact our engineers →
                </Link>
              </div>

              {/* Response time guarantee */}
              <div className="rounded-lg bg-green-50 border border-green-200 p-5 text-center">
                <div className="text-2xl font-bold text-green-700">24–48h</div>
                <div className="text-sm text-green-600 mt-1">Typical quote-routing window</div>
                <div className="text-xs text-green-500 mt-2">
                  Mon – Fri, 9:00 – 18:00 CST
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
