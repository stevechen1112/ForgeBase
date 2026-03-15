import type { Metadata } from "next";
import { RFQForm } from "@/components/forms/RFQForm";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

const BRAND = process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase";

export const metadata: Metadata = {
  title: `Request a Quotation — ${BRAND}`,
  description: "Submit your RFQ for OEM seals, custom gaskets, and precision components. Get a competitive quote within 1–2 business days.",
  robots: { index: false, follow: true },
};

interface Props {
  searchParams: Promise<{ product_id?: string; application_id?: string }>;
}

export default async function RequestQuotePage({ searchParams }: Props) {
  const sp = await searchParams;
  const productIds = sp.product_id ? [sp.product_id] : [];
  const applicationId = sp.application_id;

  return (
    <>
      <PageViewTracker pageType="rfq" />
      <main className="min-h-screen bg-gray-50 py-12 px-4">
        <div className="mx-auto max-w-5xl">
          <div className="mb-10 text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-3">Request a Quotation</h1>
            <p className="text-lg text-gray-600 max-w-2xl mx-auto">
              Fill in your requirements below. Our technical sales team will review your request and respond with a competitive quote within
              <strong> 1–2 business days</strong>.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <aside className="lg:col-span-1 space-y-6">
              <div className="rounded-lg bg-white border border-gray-200 p-5">
                <h2 className="font-semibold text-gray-800 mb-4">Why choose us?</h2>
                <ul className="space-y-3 text-sm text-gray-600">
                  {[
                    "ISO 9001:2015 certified manufacturing",
                    "OEM & custom specifications accepted",
                    "Competitive MOQ starting from 100 pcs",
                    "Global shipping to 50+ countries",
                    "Technical support from senior engineers",
                    "NDA available on request",
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
            </aside>

            <div className="lg:col-span-2 rounded-lg bg-white border border-gray-200 p-6 shadow-sm">
              <RFQForm preselectedProductIds={productIds} preselectedApplicationId={applicationId} />
            </div>
          </div>
        </div>
      </main>
    </>
  );
}