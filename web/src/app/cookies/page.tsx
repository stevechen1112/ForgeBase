import Link from "next/link";
import type { Metadata } from "next";
import { siteConfig } from "@/lib/siteConfig";

const SITE_NAME = siteConfig.brandName;

export const metadata: Metadata = {
  title: "Cookie Policy",
  description: `Cookie usage policy for the ${siteConfig.brandName} website.`,
};

export default function CookiesPage() {
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-4xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Cookie Policy</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Cookie Policy</h1>
        </div>
      </section>
      <section className="py-14">
        <div className="prose prose-gray mx-auto max-w-4xl px-6">
          <p>{SITE_NAME} uses essential website cookies and limited analytics storage to support navigation, form submissions, and basic performance measurement.</p>
          <p>Cookies may be used to remember UI state, support request flows, and understand page usage trends. They are not used to sell behavioral data to third parties.</p>
          <p>You can manage cookies through your browser settings. Disabling some cookies may affect site functionality such as form persistence or gated downloads.</p>
        </div>
      </section>
    </main>
  );
}
