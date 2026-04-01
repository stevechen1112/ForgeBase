import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedCertifications } from "@/lib/api";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { siteConfig } from "@/lib/siteConfig";

const SITE_NAME = siteConfig.brandName;

export const metadata: Metadata = {
  title: "Certifications & Quality",
  description:
    `Review ${siteConfig.brandName} quality and compliance support, including ISO workflow, RoHS and REACH documentation handling, and inspection coordination.`,
};

const SITE_URL = siteConfig.siteUrl;

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
            This section is intended for buyers who need to verify how {SITE_NAME} handles quality workflow, material compliance, and document support during export execution.
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

          {/* Documentation availability breakdown */}
          <div className="mt-12 rounded-2xl border border-gray-200 bg-white p-7">
            <h2 className="text-lg font-semibold text-gray-900">Document Availability at a Glance</h2>
            <p className="mt-1 text-sm text-gray-500 max-w-2xl">
              Buyers frequently ask which documents are available, when, and under what conditions. Below is a practical summary.
            </p>
            <div className="mt-5 grid gap-4 sm:grid-cols-3">
              {[
                {
                  type: "System certifications",
                  detail: "Facility-level certifications (e.g. ISO 9001) are available as PDF copy upon request and can be included in your order documentation package.",
                  note: "Available for all programs",
                  color: "border-green-100 bg-green-50",
                  badge: "bg-green-100 text-green-700",
                },
                {
                  type: "Product compliance docs",
                  detail: "RoHS declarations, REACH statements, material test reports, and CE support documents are generated per SKU or product family based on destination market.",
                  note: "Generated per order scope",
                  color: "border-blue-100 bg-blue-50",
                  badge: "bg-blue-100 text-blue-700",
                },
                {
                  type: "Export documentation",
                  detail: "Packing lists, carton marks, barcode accuracy control, and certificate-of-origin coordination are part of the standard export program.",
                  note: "Included in standard export",
                  color: "border-gray-100 bg-gray-50",
                  badge: "bg-gray-200 text-gray-700",
                },
              ].map((item) => (
                <div key={item.type} className={`rounded-xl border p-5 ${item.color}`}>
                  <h3 className="text-sm font-semibold text-gray-800">{item.type}</h3>
                  <p className="mt-2 text-xs leading-relaxed text-gray-600">{item.detail}</p>
                  <span className={`mt-3 inline-block rounded-full px-2.5 py-0.5 text-xs font-medium ${item.badge}`}>
                    {item.note}
                  </span>
                </div>
              ))}
            </div>
            <p className="mt-5 text-sm text-gray-500">
              Document scope varies by product family and destination market.{" "}
              <Link href="/contact" className="font-medium text-blue-600 hover:underline">
                Contact us to confirm availability for your SKU and market.
              </Link>
            </p>
          </div>
        </div>
      </section>

      {/* Quality commitment section */}
      <section className="bg-blue-50 border-t border-blue-100 py-14">
        <div className="container mx-auto max-w-3xl px-6 text-center">
          <h2 className="text-2xl font-bold text-gray-800">Our Commitment to Quality</h2>
          <p className="mt-4 text-gray-600 leading-relaxed">
            {SITE_NAME} treats quality and compliance as operational support for real orders: incoming checks,
            selected performance verification, packaging control, document accuracy, and third-party inspection coordination when programs require it.
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
