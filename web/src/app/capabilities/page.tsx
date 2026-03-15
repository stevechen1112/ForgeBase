import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedCapabilities } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

export const metadata: Metadata = {
  title: "Manufacturing Capabilities",
  description: "Explore our manufacturing processes, production strengths, and custom development capabilities.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

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
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {capabilities.map((cap) => (
              <Link key={cap.id} href={`/capabilities/${cap.slug}`} className="rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all">
                <h2 className="font-semibold text-gray-800">{cap.capability_name}</h2>
                <p className="mt-2 text-sm text-gray-500">{cap.short_description}</p>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}