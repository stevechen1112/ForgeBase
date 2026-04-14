import Link from "next/link";
import type { Metadata } from "next";
import { getPublishedCapabilities, getPublishedCertifications, getPublishedPageByType } from "@/lib/api";
import { FlexiblePageRenderer } from "@/components/pages/FlexiblePageRenderer";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildBreadcrumbSchema, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { getAboutHeroImage } from "@/lib/demoAssets";
import { getRuntimeSiteContext } from "@/lib/runtimeSiteConfig";

export async function generateMetadata(): Promise<Metadata> {
  const { siteName } = await getRuntimeSiteContext();
  const pageOverride = await getPublishedPageByType("about");

  if (pageOverride) {
    return {
      title: pageOverride.seo_title ?? pageOverride.title,
      description: pageOverride.seo_description ?? pageOverride.subtitle ?? undefined,
    };
  }

  return {
    title: `About ${siteName} | OEM Hand Tool Manufacturer in Taiwan`,
    description:
      `Learn about ${siteName}, a Taiwan-based OEM/ODM hand tool manufacturer focused on quality control, export-ready execution, and private-label tool programs.`,
  };
}

const TIMELINE = [
  { year: "2001", event: "Company founded in Taichung with a focus on export-ready hand tool programs." },
  { year: "2004", event: "Expanded into socket and ratchet-related exports for distributor and workshop channels." },
  { year: "2007", event: "Added finished hand tool assembly capability to improve sample-to-production control." },
  { year: "2011", event: "Launched OEM toolkit packaging service for private-label assortment programs." },
  { year: "2014", event: "Expanded insulated-tool coverage for electrical and utility-oriented buyers." },
  { year: "2017", event: "Formalized torque verification workflow for controlled fastening programs." },
  { year: "2023", event: "Optimized kit assembly and export packaging operations for mixed-SKU programs." },
];

const getProductLines = (siteName: string) => [
  {
    title: "Torque and Socket Tools",
    desc: "Built for automotive service, industrial maintenance, and controlled fastening programs where repeatable torque and dependable fit matter.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.562.562 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
      </svg>
    ),
  },
  {
    title: "Insulated Electrical Tools",
    desc: "Professional insulated tool systems for electrical contractors, utilities, and safety-sensitive maintenance teams.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
      </svg>
    ),
  },
  {
    title: "Workshop and Striking Tools",
    desc: "Workshop-ready hammers, mallets, pry bars, and punch sets designed for daily mechanical use rather than one-off retail novelty.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
      </svg>
    ),
  },
  {
    title: "Automotive and Toolkit Programs",
    desc: `${siteName} supports service-tool assortments, mechanic drawer sets, electrical kits, and other programs that combine tools, packaging, and documentation.`,
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

const getOperationalStrengths = (siteName: string) => [
  {
    title: "Engineering Review",
    desc: `Standard items can move quickly, but custom items still require responsible review. ${siteName} supports specification clarification, selection guidance, and selected customization planning before mass production begins.`,
  },
  {
    title: "Quality Workflow",
    desc: "Incoming material checks, dimensional verification, selected hardness validation, torque-related performance control, and pre-packing inspections are used to reduce avoidable variation.",
  },
  {
    title: "Packaging and OEM Readiness",
    desc: "Retail packaging, molded cases, EVA foam organization, barcode labels, instruction inserts, and carton markings are treated as part of the product program rather than afterthoughts.",
  },
  {
    title: "Export Communication",
    desc: `${siteName} positions communication clarity as part of the offer because document mistakes and shipment ambiguity carry real cost for importers and distributors.`,
  },
];

export default async function AboutPage() {
  const { siteUrl: SITE_URL, siteName: SITE_NAME, siteConfig: runtimeSiteConfig } = await getRuntimeSiteContext();
  const pageOverride = await getPublishedPageByType("about");

  if (pageOverride) {
    return <FlexiblePageRenderer page={pageOverride} />;
  }

  const productLines = getProductLines(SITE_NAME);
  const operationalStrengths = getOperationalStrengths(SITE_NAME);
  const [capabilities, certifications] = await Promise.all([
    getPublishedCapabilities(),
    getPublishedCertifications(),
  ]);

  return (
    <>
      <PageViewTracker pageType="about" />
      <StructuredData
        data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
      />
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "About", url: `${SITE_URL}/about` },
        ])}
      />

      {/* ── Hero header ── */}
      <section className="relative overflow-hidden border-b border-gray-100 py-16 text-white">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${getAboutHeroImage(runtimeSiteConfig)})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/85 via-blue-950/78 to-blue-900/50" />
        <div className="mx-auto max-w-6xl px-6">
          <nav aria-label="Breadcrumb" className="relative mb-4 text-xs text-blue-300">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1.5">/</span>
            <span>About</span>
          </nav>
          <h1 className="relative text-4xl font-extrabold">About {SITE_NAME}</h1>
          <p className="relative mt-3 max-w-2xl text-lg text-blue-200 leading-relaxed">
            Built for buyers who need more than a supplier. {SITE_NAME} supports professional hand tool programs with stronger process control,
            private-label readiness, and dependable communication.
          </p>
        </div>
      </section>

      {/* ── Stats strip ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid grid-cols-2 divide-x divide-y divide-gray-100 sm:grid-cols-4 sm:divide-y-0">
            {[
              { value: "20+", label: "Years in Export Tooling" },
              { value: "5", label: "Core Product Families" },
              { value: "40+", label: "Countries Served" },
              { value: "OEM / ODM", label: "Private-Label Ready" },
            ].map((s) => (
              <div key={s.label} className="flex flex-col items-center py-8 text-center">
                <span className="text-3xl font-extrabold text-blue-700">{s.value}</span>
                <span className="mt-1 text-sm text-gray-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Company story ── */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
            <div>
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">Our Story</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Built for Buyers Who Need More Than a Factory</h2>
              <p className="mt-4 leading-relaxed text-gray-600">
                {SITE_NAME} Co., Ltd. was built around a simple commercial reality: many buyers can find factories,
                but far fewer can find manufacturers that keep product, packaging, and shipment details together consistently over time.
                That gap is where {SITE_NAME} competes.
              </p>
              <p className="mt-4 leading-relaxed text-gray-600">
                The company supports tool brands, distributors, and industrial buyers who need a practical manufacturing partner rather than a low-visibility supply source.
                Its strength is not one hero product. Its strength is the ability to support a repeatable B2B tool program with clearer engineering communication,
                more stable production control, and better export discipline.
              </p>
              <p className="mt-4 leading-relaxed text-gray-600">
                Founder Ethan K. Liao entered the tooling and export sector after years of working with overseas buyers frustrated by preventable supplier problems:
                unclear revision control, packaging inconsistency, weak sample-to-production alignment, and poor shipment communication.
                {SITE_NAME} was established to close that gap.
              </p>
              <Link
                href="/contact"
                className="mt-8 inline-flex items-center gap-2 rounded-lg bg-blue-700 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-800 transition-colors"
              >
                Talk to Our Team
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>

            {/* Factory illustration placeholder */}
            <div className="overflow-hidden rounded-2xl border border-blue-100 bg-white shadow-sm">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={getAboutHeroImage(runtimeSiteConfig) ?? undefined}
                alt={`${SITE_NAME} factory and manufacturing environment`}
                className="aspect-video w-full object-cover"
              />
            </div>
          </div>
        </div>
      </section>

      {/* ── Core values ── */}
      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">What We Make</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">Professional Tool Lines for Repeat Programs</h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {productLines.map((v) => (
              <div key={v.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-100 text-blue-700">
                  {v.icon}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{v.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Timeline ── */}
      <section className="py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">Our Journey</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">Milestones</h2>
          </div>
          <div className="relative mt-12 ml-4 border-l-2 border-blue-200 pl-8 sm:ml-24 space-y-8">
            {TIMELINE.map((item) => (
              <div key={item.year} className="relative">
                {/* Dot */}
                <div className="absolute -left-[2.6rem] flex h-5 w-5 items-center justify-center rounded-full border-2 border-blue-400 bg-white">
                  <div className="h-2 w-2 rounded-full bg-blue-500" />
                </div>
                <span className="text-xs font-bold uppercase tracking-widest text-blue-600">{item.year}</span>
                <p className="mt-1 text-sm leading-relaxed text-gray-700">{item.event}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Leadership team ── */}
      <section className="bg-gray-50 py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">Operational Strengths</span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">How {SITE_NAME} Reduces Buyer Friction</h2>
          </div>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {operationalStrengths.map((item) => (
              <div key={item.title} className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="text-base font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Capabilities ── */}
      {capabilities.length > 0 && (
        <section className="py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">What We Do</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Manufacturing Capabilities</h2>
            </div>
            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {capabilities.map((cap) => (
                <Link
                  key={cap.id}
                  href={`/capabilities/${cap.slug}`}
                  className="flex flex-col rounded-xl border border-gray-100 bg-gray-50 p-6 shadow-sm hover:border-blue-200 hover:shadow-md transition-all"
                >
                  {cap.icon_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={cap.icon_url} alt="" className="mb-3 h-10 w-10 object-contain" aria-hidden="true" />
                  ) : (
                    <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-base font-bold text-blue-700">
                      {cap.capability_name.charAt(0)}
                    </div>
                  )}
                  <h3 className="font-semibold text-gray-900">{cap.capability_name}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-gray-500">{cap.short_description}</p>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">Quality Assurance</span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Certifications</h2>
            </div>
            <div className="mt-12 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── CTA ── */}
      <section className="bg-blue-900 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold">Ready to Work Together?</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            If you are building a professional hand tool line, a service-tool assortment, or a private-label toolkit program,
            {SITE_NAME} can help structure a cleaner sourcing workflow from product selection to shipment execution.
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/contact"
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              Contact Our Team
            </Link>
            <Link
              href="/products"
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              Browse Products
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
