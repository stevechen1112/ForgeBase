import Link from "next/link";
import type { Metadata } from "next";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();

  return {
    title: "News & Updates",
    description: `Latest company updates, manufacturing milestones, and product news from ${siteName}.`,
  };
}

const getNews = (siteName: string) => [
  { date: "2026-02-10", title: `${siteName} expands insulated tool line for utility buyers`, summary: "New VDE-aligned insulated sets added for contractors, utilities, and private-label programs." },
  { date: "2025-11-22", title: "Factory calibration workflow upgraded for torque verification", summary: "Additional calibration checkpoints introduced to improve repeatability in high-volume torque wrench programs." },
  { date: "2025-08-15", title: `${siteName} adds mixed-SKU export packing support`, summary: "Consolidated packing workflows now support distributor assortments and multi-market shipping programs." },
];

export default async function NewsPage() {
  const { siteName: SITE_NAME } = await getRuntimeSiteContext();
  const NEWS = getNews(SITE_NAME);
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">News & Updates</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">News & Updates</h1>
          <p className="mt-3 max-w-2xl text-gray-600">Recent updates on product development, quality workflow, packaging capability, and export execution relevant to buyers and distributor programs.</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 space-y-6">
          {NEWS.map((item) => (
            <article key={item.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-widest text-blue-600">{item.date}</p>
              <h2 className="mt-2 text-xl font-semibold text-gray-900">{item.title}</h2>
              <p className="mt-3 text-sm leading-relaxed text-gray-600">{item.summary}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
