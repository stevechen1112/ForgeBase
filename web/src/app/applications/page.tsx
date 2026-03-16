import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedApplications } from "@/lib/api";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";

export const metadata: Metadata = {
  title: "Industry Applications",
  description:
    "Explore how our products are used across industries — from automotive to electronics to construction.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

export default async function ApplicationsPage() {
  const res = await getPublishedApplications("en", 1, 50);
  const applications = res.data;

  // Group by industry
  const byIndustry = applications.reduce<Record<string, typeof applications>>(
    (acc, app) => {
      const key = app.industry || "Other";
      if (!acc[key]) acc[key] = [];
      acc[key].push(app);
      return acc;
    },
    {}
  );

  return (
    <>
      <ChatWidget contextPage="/applications" contextEntityType="application" />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Applications", url: `${SITE_URL}/applications` },
        ])}
      />

      {/* Page header */}
      <section className="bg-gray-50 border-b border-gray-100 py-12">
        <div className="container mx-auto max-w-5xl px-6">
          <nav aria-label="Breadcrumb" className="mb-3 text-xs text-gray-400">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1">/</span>
            <span className="text-gray-600">Applications</span>
          </nav>
          <h1 className="text-3xl font-bold text-gray-800">Industry Applications</h1>
          <p className="mt-2 text-gray-500 max-w-2xl">
            Discover how our solutions address real-world challenges across key industries.
          </p>
        </div>
      </section>

      {/* Content */}
      <section className="py-12">
        <div className="container mx-auto max-w-5xl px-6">
          {applications.length === 0 ? (
            <p className="text-center text-gray-500 py-16">No applications published yet.</p>
          ) : Object.keys(byIndustry).length > 1 ? (
            // Multi-industry grouped view
            Object.entries(byIndustry).map(([industry, apps]) => (
              <div key={industry} className="mb-12">
                <h2 className="text-lg font-semibold text-gray-700 mb-4 border-b border-gray-100 pb-2">
                  {industry}
                </h2>
                <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                  {apps.map((app) => (
                    <ApplicationCard key={app.id} application={app} />
                  ))}
                </div>
              </div>
            ))
          ) : (
            // Single industry or mixed — flat grid
            <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} />
              ))}
            </div>
          )}
        </div>
      </section>
    </>
  );
}
