import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedCapabilities } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { siteConfig } from "@/lib/siteConfig";

const SITE_NAME = siteConfig.brandName;

export const metadata: Metadata = {
  title: "Manufacturing Capabilities",
  description: `Explore ${siteConfig.brandName} capabilities including OEM development, private-label packaging, torque inspection, kit assembly, and export documentation support.`,
};

const SITE_URL = siteConfig.siteUrl;

// Maps common capability category tags to a short buyer-facing benefit statement
const BUYER_BENEFIT: Record<string, string> = {
  engineering: "Reduces revision cycles between buyer spec and production.",
  quality: "Gives repeat-order buyers a consistent inspection baseline.",
  packaging: "Supports OEM, private-label, and retail-ready delivery formats.",
  assembly: "Enables mixed-SKU kits and toolkit programs without enterprise complexity.",
  export: "Ensures shipment documentation accuracy for target markets.",
  testing: "Provides traceable torque and performance verification per batch.",
};

export default async function CapabilitiesPage() {
  const capabilities = await getPublishedCapabilities();

  return (
    <>
      <PageViewTracker pageType="capability" />
      <StructuredData data={buildBreadcrumbSchema([{ name: "Home", url: SITE_URL }, { name: "Capabilities", url: `${SITE_URL}/capabilities` }])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Capabilities</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">Manufacturing Capabilities</h1>
          <p className="mt-2 max-w-2xl text-gray-500">
            These pages explain the operational strengths behind the {SITE_NAME} catalog — so buyers can judge whether the supplier fits their commercial workflow, not just their tool list.
          </p>
          <div className="mt-5 flex flex-wrap gap-2 text-xs text-gray-400">
            {["OEM development", "Private-label packaging", "Torque verification", "Kit assembly", "Export documentation"].map((tag) => (
              <span key={tag} className="rounded-full border border-gray-200 bg-white px-3 py-1">{tag}</span>
            ))}
          </div>
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap) => {
              const buyerBenefit = cap.category_tag ? (BUYER_BENEFIT[cap.category_tag.toLowerCase()] ?? null) : null;
              return (
                <Link key={cap.id} href={`/capabilities/${cap.slug}`} className="group rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all">
                  {cap.category_tag && (
                    <span className="mb-2 inline-block rounded-full bg-blue-50 px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide text-blue-600">
                      {cap.category_tag}
                    </span>
                  )}
                  <h2 className="font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">{cap.capability_name}</h2>
                  <p className="mt-2 text-sm text-gray-500">{cap.short_description}</p>
                  {buyerBenefit && (
                    <p className="mt-3 text-xs text-blue-600 border-t border-gray-100 pt-3">{buyerBenefit}</p>
                  )}
                </Link>
              );
            })}
          </div>

          <div className="mt-10 rounded-2xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">Not sure which capability matters most for your program?</h2>
            <p className="mt-2 max-w-3xl text-sm leading-relaxed text-blue-800">
              Describe your sourcing scenario — toolkit build, private-label launch, or recurring distributor supply — and {SITE_NAME} can identify which capabilities are most relevant to your execution flow.
            </p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link href="/contact" className="rounded-lg bg-blue-700 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                Discuss Your Program
              </Link>
              <Link href="/rfq" className="rounded-lg border border-blue-300 bg-white px-5 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-100 transition-colors">
                Submit RFQ
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}