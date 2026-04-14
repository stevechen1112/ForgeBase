import Link from "next/link";
import type { Metadata } from "next";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();

  return {
    title: "Terms of Service",
    description: `Terms governing the use of the ${siteName} website and business enquiry channels.`,
  };
}

export default async function TermsPage() {
  const { siteName: SITE_NAME } = await getRuntimeSiteContext();
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Terms of Service</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Terms of Service</h1>
        </div>
      </section>
      <section className="py-14">
        <div className="prose prose-gray mx-auto max-w-4xl px-6">
          <p>This website is provided for product presentation, business enquiry, RFQ intake, and technical document access related to {SITE_NAME}.</p>
          <p>Specifications, availability, lead times, and pricing shown on the website are illustrative unless otherwise confirmed in a written quotation or sales agreement.</p>
          <p>Use of this website does not create a supply contract. Final terms are governed by issued quotations, purchase orders, and mutually agreed commercial terms.</p>
        </div>
      </section>
    </main>
  );
}
