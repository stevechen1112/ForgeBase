import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Dealer Locator",
  description: "Regional distributor and dealer support information for NorthForge Tools.",
};

const REGIONS = [
  "East Asia and Southeast Asia",
  "European distribution partners",
  "Australia and Oceania",
  "Private-label importer programs in North America",
];

export default function DealersPage() {
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Dealer Locator</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Dealer Locator</h1>
          <p className="mt-3 max-w-2xl text-gray-600">NorthForge works with importers, distributors, and private-label partners across multiple regions.</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 grid gap-8 lg:grid-cols-[1fr,0.9fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">Supported Regions</h2>
            <ul className="mt-4 space-y-3 text-sm text-gray-600">
              {REGIONS.map((region) => (
                <li key={region} className="rounded-lg bg-gray-50 px-4 py-3">{region}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">Need a regional contact?</h2>
            <p className="mt-3 text-sm leading-relaxed text-blue-800">Contact sales@northforge-tools.com with your country, target channels, and product categories. We will route you to the correct sales contact or distributor support team.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
