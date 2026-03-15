import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedCertifications } from "@/lib/api";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

export const metadata: Metadata = {
  title: "Certifications & Quality",
  description:
    "Our internationally recognised certifications and quality management standards.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export default async function CertificationsPage() {
  const certifications = await getPublishedCertifications();

  return (
    <>
      <PageViewTracker pageType="certification" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Certifications", url: `${SITE_URL}/certifications` },
        ])}
      />

      {/* Header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Certifications</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">Quality &amp; Certifications</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            Every product we manufacture meets rigorous international quality and safety standards.
          </p>
        </div>
      </section>

      {/* Certificates grid */}
      <section className="py-14">
        <div className="container mx-auto max-w-5xl px-6">
          {certifications.length === 0 ? (
            <p className="text-center text-gray-500 py-16">
              No certifications published yet.
            </p>
          ) : (
            <div className="grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Quality commitment section */}
      <section className="bg-blue-50 border-t border-blue-100 py-14">
        <div className="container mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-bold text-gray-800">Our Commitment to Quality</h2>
          <p className="mt-4 text-gray-600 leading-relaxed">
            We follow a rigorous quality management process from raw material sourcing to final
            inspection. Our manufacturing facilities are regularly audited by independent third
            parties to ensure full compliance with international standards.
          </p>
          <Link
            href="/contact"
            className="mt-8 inline-block rounded-lg bg-blue-700 px-8 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
          >
            Request Quality Documentation
          </Link>
        </div>
      </section>
    </>
  );
}
