import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import { getCertificationBySlug } from "@/lib/api";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

type Props = { params: Promise<{ slug: string }> };

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const certification = await getCertificationBySlug(slug);
  if (!certification) return { title: "Not Found" };
  return {
    title: certification.cert_name,
    description: certification.description || certification.issuer || undefined,
  };
}

export default async function CertificationDetailPage({ params }: Props) {
  const { slug } = await params;
  const certification = await getCertificationBySlug(slug);
  if (!certification) notFound();

  return (
    <>
      <PageViewTracker pageType="certification" pageId={certification.id} />
      <StructuredData data={buildBreadcrumbSchema([
        { name: "Home", url: SITE_URL },
        { name: "Certifications", url: `${SITE_URL}/certifications` },
        { name: certification.cert_name, url: `${SITE_URL}/certifications/${slug}` },
      ])} />

      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <Link href="/certifications" className="hover:underline">Certifications</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">{certification.cert_name}</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">{certification.cert_name}</h1>
          {certification.issuer && <p className="mt-2 text-gray-500">Issued by {certification.issuer}</p>}
        </div>
      </section>

      <section className="py-14">
        <div className="container mx-auto max-w-4xl px-6 grid gap-8 lg:grid-cols-[220px,1fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-6 flex items-center justify-center">
            {certification.badge_image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={certification.badge_image_url} alt={certification.cert_name} className="max-h-36 object-contain" />
            ) : (
              <div className="text-sm text-gray-400">No badge image</div>
            )}
          </div>
          <div>
            <div className="prose prose-gray max-w-none text-gray-700 whitespace-pre-line">
              {certification.description || "Certification details will be updated soon."}
            </div>
            <dl className="mt-6 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">Certificate No.</dt><dd className="font-medium text-gray-700">{certification.cert_number || "—"}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">Locale</dt><dd className="font-medium text-gray-700">{certification.locale}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">Issued</dt><dd className="font-medium text-gray-700">{certification.issued_at ? new Date(certification.issued_at).toLocaleDateString() : "—"}</dd></div>
              <div className="rounded-lg bg-gray-50 px-4 py-3"><dt className="text-gray-500">Expires</dt><dd className="font-medium text-gray-700">{certification.expires_at ? new Date(certification.expires_at).toLocaleDateString() : "—"}</dd></div>
            </dl>
            {certification.document_url && (
              <a href={certification.document_url} target="_blank" rel="noopener noreferrer" className="mt-6 inline-block rounded-lg bg-blue-700 px-6 py-3 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                Download Certificate
              </a>
            )}
          </div>
        </div>
      </section>
    </>
  );
}