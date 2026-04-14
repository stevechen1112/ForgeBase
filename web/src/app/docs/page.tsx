import Link from "next/link";
import type { Metadata } from "next";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();

  return {
    title: "Technical Docs",
    description: `Technical documentation, data sheets, and compliance documents for ${siteName} products.`,
  };
}

const DOCS = [
  { title: "Product spec sheets", desc: "Available from individual product pages through the download panel." },
  { title: "Compliance certificates", desc: "Available from the certifications section, including ISO, RoHS, and REACH-related support files." },
  { title: "OEM documentation", desc: "Shared during RFQ and sampling stages based on project requirements." },
];

export default function DocsPage() {
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Technical Docs</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Technical Docs</h1>
          <p className="mt-3 max-w-2xl text-gray-600">Documentation access is organized around product pages, compliance pages, and RFQ workflows so buyers can request the right files at the right stage.</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 grid gap-6 md:grid-cols-3">
          {DOCS.map((doc) => (
            <div key={doc.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h2 className="text-lg font-semibold text-gray-900">{doc.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-600">{doc.desc}</p>
            </div>
          ))}
        </div>
        <div className="mx-auto mt-8 max-w-5xl px-6">
          <div className="rounded-2xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">Document access note</h2>
            <p className="mt-2 text-sm leading-relaxed text-blue-800">
              Some files are shared only after product scope or compliance relevance is confirmed, especially for OEM programs, customer-specific labeling, or audit-sensitive requests.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}
