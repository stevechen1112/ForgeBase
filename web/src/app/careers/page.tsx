import Link from "next/link";
import type { Metadata } from "next";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();

  return {
    title: "Careers",
    description: `Career opportunities and hiring information for ${siteName}.`,
  };
}

const OPENINGS = [
  "International Sales Executive",
  "Quality Assurance Engineer",
  "OEM Project Coordinator",
  "Packaging and Logistics Planner",
];

export default async function CareersPage() {
  const { siteName: SITE_NAME, careersEmail } = await getRuntimeSiteContext();
  return (
    <main>
      <section className="border-b border-gray-100 bg-gray-50 py-14">
        <div className="mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Careers</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-900">Careers</h1>
          <p className="mt-3 max-w-2xl text-gray-600">{SITE_NAME} hires across sales, quality, packaging, manufacturing coordination, and export operations to support real B2B tool programs.</p>
        </div>
      </section>
      <section className="py-14">
        <div className="mx-auto max-w-5xl px-6 grid gap-8 lg:grid-cols-[1.2fr,0.8fr]">
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h2 className="text-xl font-semibold text-gray-900">Current Focus Roles</h2>
            <ul className="mt-4 space-y-3 text-sm text-gray-600">
              {OPENINGS.map((role) => (
                <li key={role} className="rounded-lg bg-gray-50 px-4 py-3">{role}</li>
              ))}
            </ul>
          </div>
          <div className="rounded-xl border border-blue-100 bg-blue-50 p-6">
            <h2 className="text-lg font-semibold text-blue-900">Apply by Email</h2>
            <p className="mt-3 text-sm leading-relaxed text-blue-800">Send your resume and role interest to {careersEmail}. Include language skills, manufacturing experience, and export market exposure where relevant.</p>
          </div>
        </div>
      </section>
    </main>
  );
}
