import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCapabilityBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

type Props = { params: Promise<{ slug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const capability = await getCapabilityBySlug(slug);
  if (!capability) return { title: "Not Found" };
  return {
    title: capability.capability_name,
    description: capability.short_description,
  };
}

export default async function CapabilityDetailPage({ params }: Props) {
  const { slug } = await params;
  const capability = await getCapabilityBySlug(slug);
  if (!capability) notFound();

  return (
    <>
      <PageViewTracker pageType="capability" pageId={capability.id} />
      <StructuredData data={buildBreadcrumbSchema([
        { name: "Home", url: SITE_URL },
        { name: "Capabilities", url: `${SITE_URL}/capabilities` },
        { name: capability.capability_name, url: `${SITE_URL}/capabilities/${capability.slug}` },
      ])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/capabilities" className="hover:underline">Capabilities</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{capability.capability_name}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{capability.capability_name}</h1>
          <p className="mt-3 text-gray-500 max-w-2xl">{capability.short_description}</p>
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6 grid gap-8 lg:grid-cols-2">
          <div>
            <div className="prose prose-gray max-w-none text-gray-700 whitespace-pre-line">
              {capability.detail || capability.short_description}
            </div>
          </div>
          <div className="rounded-xl border border-gray-200 bg-gray-50 p-6">
            <h2 className="text-lg font-semibold text-gray-800 mb-3">Capability Snapshot</h2>
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between gap-4"><dt className="text-gray-500">Category</dt><dd className="font-medium text-gray-700">{capability.category_tag || "General"}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-gray-500">Locale</dt><dd className="font-medium text-gray-700">{capability.locale}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-gray-500">Status</dt><dd className="font-medium text-gray-700">{capability.status}</dd></div>
            </dl>
          </div>
        </div>
      </section>
    </>
  );
}