import Link from "next/link";
import type { Metadata } from "next";
import {
  getPublishedCategories,
  getPublishedApplications,
  getPublishedCertifications,
  getFeaturedProducts,
} from "@/lib/api";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { ChatWidget } from "@/components/chat/ChatWidget";
import { StructuredData, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { HOME_HERO_IMAGE, getCategoryCardImage, getProductImage } from "@/lib/demoAssets";

export const metadata: Metadata = {
  title: "NorthForge Tools | OEM Hand Tool Manufacturer in Taiwan",
  description:
    "Taiwan-based OEM/ODM hand tool manufacturer specializing in torque tools, insulated tools, workshop tools, and private-label toolkit programs for distributors and tool brands.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME === "ForgeBase"
  ? "NorthForge Tools"
  : (process.env.NEXT_PUBLIC_SITE_NAME || "NorthForge Tools");

const STATS = [
  { value: "20+", label: "Years Export Experience" },
  { value: "30+", label: "Core Demo SKUs" },
  { value: "40+", label: "Countries Served" },
  { value: "98%", label: "Shipment-Readiness KPI" },
];

const WHY_US = [
  {
    title: "Stable Repeat Orders",
    desc: "NorthForge reduces drift between approved samples and recurring production through tighter drawing control, verification workflow, and packaging discipline.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "OEM and Private Label Execution",
    desc: "From logo application and insert cards to barcode labels and retail-ready assortments, NorthForge supports programs that need more than loose tools in cartons.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.017-.017c.372-.372.596-.878.596-1.414 0-.523-.199-1.026-.554-1.403L9.62 5.498a1.875 1.875 0 00-2.346-.271l-1.16.58z" />
      </svg>
    ),
  },
  {
    title: "Documentation Discipline",
    desc: "Export buyers need clean packing lists, carton marks, barcode accuracy, and compliance-support paperwork. NorthForge treats those details as part of the product program.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
      </svg>
    ),
  },
  {
    title: "Mixed-SKU Program Flexibility",
    desc: "The team is structured to support recurring mixed-SKU programs, toolkit builds, and distributor-ready assortments without enterprise-scale complexity.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    ),
  },
  {
    title: "Tool-Focused Product Scope",
    desc: "The catalog is built around torque tools, insulated tools, workshop tools, automotive service tools, and custom toolkit programs for professional channels.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "Compliance-Support Ready",
    desc: "NorthForge supports ISO 9001 workflow, insulated-tool process discipline, RoHS and REACH documentation, and third-party inspection coordination when needed.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const OEM_FLOW = [
  {
    title: "Define Product Scope",
    desc: "Clarify target market, usage scenario, and whether a standard catalog item or customization path makes more commercial sense.",
  },
  {
    title: "Review Branding and Packaging",
    desc: "Confirm logo application, insert cards, molded cases, barcode labels, and carton marking requirements before sampling.",
  },
  {
    title: "Approve Samples and Key Specs",
    desc: "Lock in critical details such as torque range, insulation class, hardness targets, finish, packaging format, and inspection points.",
  },
  {
    title: "Move into Controlled Production",
    desc: "Production, packing, export documentation, and shipment readiness are managed as one workflow so the program stays consistent after approval.",
  },
];

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const [categories, applicationsRes, certifications, featuredProducts] = await Promise.all([
    getPublishedCategories(locale),
    getPublishedApplications(locale),
    getPublishedCertifications(locale),
    getFeaturedProducts(locale),
  ]);
  const applications = applicationsRes.data.slice(0, 6);
  const categorySlugById = new Map(categories.map((category) => [category.id, category.slug]));

  return (
    <>
      <PageViewTracker pageType="home" />
      <ChatWidget contextPage="/" contextEntityType="home" />
      <StructuredData
        data={buildOrganizationSchema({ name: SITE_NAME, url: SITE_URL })}
      />

      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-blue-950 text-white">
        <div
          className="absolute inset-0 bg-cover bg-center"
          style={{ backgroundImage: `url(${HOME_HERO_IMAGE})` }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-slate-950/90 via-blue-950/80 to-blue-900/55" />
        {/* Background grid pattern */}
        <div
          className="pointer-events-none absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              "linear-gradient(white 1px, transparent 1px), linear-gradient(90deg, white 1px, transparent 1px)",
            backgroundSize: "40px 40px",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-6 py-28 sm:py-36">
          <div className="flex flex-col items-center text-center">
            {/* Eyebrow */}
            <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-blue-200">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-400" />
              Trusted Export Manufacturer for Professional Tool Programs
            </span>

            <h1 className="max-w-4xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              Precision-Built Hand Tools for Brands,
              <br />
              <span className="text-blue-300">Distributors, and Industrial Buyers</span>
            </h1>

            <p className="mx-auto mt-5 max-w-3xl text-lg leading-relaxed text-blue-100">
              NorthForge Tools helps importers, private-label brands, and industrial distributors source torque tools,
              insulated tools, workshop tools, and custom toolkit programs with stronger quality control and cleaner export execution.
            </p>

            <div className="mt-9 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href="/rfq"
                className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
              >
                Request a Quote
              </Link>
              <Link
                href="/products"
                className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
              >
                Browse Products →
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Trust bar / Stats ── */}
      <section className="border-b border-gray-100 bg-white">
        <div className="mx-auto max-w-6xl px-6 py-10">
          <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            {STATS.map((s) => (
              <div key={s.label} className="flex flex-col items-center text-center">
                <span className="text-3xl font-extrabold text-blue-700">{s.value}</span>
                <span className="mt-1 text-sm text-gray-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Featured Products ── */}
      {featuredProducts.length > 0 && (
        <section className="bg-white py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                Featured
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Selected Tool Lines</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                Representative SKUs across torque, insulated, workshop, automotive service, and toolkit programs.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {featuredProducts.map((product) => (
                <Link
                  key={product.id}
                  href={categorySlugById.get(product.category_id) ? `/products/${categorySlugById.get(product.category_id)}/${product.slug}` : "/products"}
                  className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <div className="mb-3 h-32 w-full overflow-hidden rounded-lg bg-blue-50">
                    {getProductImage(product, categorySlugById.get(product.category_id)) ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={getProductImage(product, categorySlugById.get(product.category_id)) ?? undefined}
                        alt={product.product_name}
                        className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
                      />
                    ) : (
                      <div className="flex h-full items-center justify-center text-4xl text-blue-300 group-hover:bg-blue-100 transition-colors">
                        ⬡
                      </div>
                    )}
                  </div>
                  <h3 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors">
                    {product.product_name}
                  </h3>
                  <p className="mt-1 text-xs text-gray-500">{product.model_number}</p>
                  <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-gray-500">
                    {product.short_description}
                  </p>
                  <span className="mt-3 text-xs font-semibold text-blue-600 group-hover:underline">
                    View Details →
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/products"
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                Browse All Products
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Product Categories ── */}
      {categories.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                Our Catalogue
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Product Categories</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                Browse the core families NorthForge builds for distributor programs, private-label launches, and industrial buying teams.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              {categories.map((cat) => (
                <Link
                  key={cat.id}
                  href={`/products/${cat.slug}`}
                  className="group flex flex-col items-center rounded-xl border border-gray-200 bg-white p-6 text-center shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  {getCategoryCardImage(cat) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={getCategoryCardImage(cat) ?? undefined}
                      alt={cat.category_name}
                      className="mb-3 h-20 w-full rounded-lg object-cover"
                    />
                  ) : (
                    <span className="mb-3 flex h-20 w-full items-center justify-center rounded-lg bg-blue-50 text-3xl group-hover:bg-blue-100 transition-colors">
                      ⬡
                    </span>
                  )}
                  <span className="text-sm font-semibold text-gray-800 group-hover:text-blue-700 transition-colors">
                    {cat.category_name}
                  </span>
                </Link>
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/products"
                className="inline-flex items-center gap-1 rounded-lg border border-blue-200 bg-white px-6 py-2.5 text-sm font-semibold text-blue-700 hover:bg-blue-50 transition-colors"
              >
                View Full Catalogue
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
                </svg>
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── Why Choose Us ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              Why NorthForge
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">Built for Global Buyers</h2>
            <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
              Everything we do is designed to make your sourcing simpler, safer, and more profitable.
            </p>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {WHY_US.map((item) => (
              <div
                key={item.title}
                className="rounded-xl border border-gray-100 bg-gray-50 p-6 hover:border-blue-200 hover:bg-blue-50/30 transition-colors"
              >
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-100 text-blue-700">
                  {item.icon}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Applications ── */}
      {applications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                Industries
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Featured Applications</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                NorthForge focuses on programs where repeatability, packaging control, and clean documentation matter as much as the tool itself.
              </p>
            </div>

            <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
              {applications.map((app) => (
                <ApplicationCard key={app.id} application={app} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/applications"
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                View all industries →
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── OEM / ODM flow ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              OEM / ODM Flow
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">How a Tool Program Moves Forward</h2>
            <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
              The process is designed to keep product, packaging, and shipment execution aligned from the first discussion through recurring orders.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-4">
            {OEM_FLOW.map((step, index) => (
              <div key={step.title} className="rounded-xl border border-gray-100 bg-gray-50 p-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-700 text-sm font-bold text-white">
                  0{index + 1}
                </div>
                <h3 className="mt-4 text-base font-semibold text-gray-900">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-gray-600">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Certifications ── */}
      {certifications.length > 0 && (
        <section className="bg-gray-50 py-20">
          <div className="mx-auto max-w-6xl px-6">
            <div className="text-center">
              <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
                Quality Assurance
              </span>
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Certifications &amp; Standards</h2>
              <p className="mx-auto mt-3 max-w-2xl text-base text-gray-500">
                Compliance support is positioned as a working part of export execution, not a footer claim added after the tooling is done.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-2 gap-5 sm:grid-cols-3 lg:grid-cols-4">
              {certifications.map((cert) => (
                <CertificationBadge key={cert.id} certification={cert} />
              ))}
            </div>

            <div className="mt-10 text-center">
              <Link
                href="/certifications"
                className="inline-flex items-center gap-1 text-sm font-semibold text-blue-700 hover:underline"
              >
                View all certifications →
              </Link>
            </div>
          </div>
        </section>
      )}

      {/* ── CTA Banner ── */}
      <section className="bg-blue-900 py-20 text-white">
        <div className="mx-auto max-w-4xl px-6 text-center">
          <h2 className="text-3xl font-bold">Build a Cleaner, More Reliable Tool Program</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            Whether you need recurring catalog supply, private-label packaging, or a custom toolkit assortment,
            NorthForge can help structure the right sourcing program for your market.
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/rfq"
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              Request a Quote
            </Link>
            <Link
              href="/contact"
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              Contact Sales
            </Link>
          </div>
          <p className="mt-6 text-xs text-blue-400">
            Response within 1 business day for qualified enquiries
          </p>
        </div>
      </section>
    </>
  );
}
