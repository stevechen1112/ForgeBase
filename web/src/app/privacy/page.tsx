import Link from "next/link";
import type { Metadata } from "next";
import { siteConfig } from "@/lib/siteConfig";

const SITE_NAME = siteConfig.brandName;

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: `Privacy policy for ${siteConfig.brandName} website enquiries and document requests.`,
};

export default function PrivacyPage() {
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Privacy Policy</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Privacy Policy</h1>
        </div>
      </section>
      <section className="py-14">
        <div className="prose prose-gray mx-auto max-w-4xl px-6">
          <p>{SITE_NAME} collects enquiry details, quotation requests, and document request information only for business response, sales follow-up, and customer support purposes.</p>
          <p>Submitted information may include your name, company, email, phone number, country, and product interest. We do not sell personal data to third parties.</p>
          <p>Information is retained only as long as needed for commercial communication, compliance, and recordkeeping. You may request correction or deletion by contacting {siteConfig.contactEmail}.</p>
        </div>
      </section>
    </main>
  );
}
