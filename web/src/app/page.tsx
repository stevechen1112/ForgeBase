import Link from "next/link";
import type { Metadata } from "next";
import {
  getPublishedCategories,
  getPublishedApplications,
  getPublishedCertifications,
  getCTAByKey,
  getFeaturedProducts,
} from "@/lib/api";
import { ApplicationCard } from "@/components/ui/ApplicationCard";
import { CertificationBadge } from "@/components/ui/CertificationBadge";
import { StructuredData, buildOrganizationSchema } from "@/components/seo/StructuredData";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";
import { HOME_HERO_IMAGE, getCategoryCardImage } from "@/lib/demoAssets";

export const metadata: Metadata = {
  title: "Home",
  description:
    "Global manufacturing solutions — quality products, industry applications, and international certifications.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";
const SITE_NAME = process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase";

const STATS = [
  { value: "40+",  label: "Countries Served" },
  { value: "500+", label: "Product SKUs" },
  { value: "20+",  label: "Years Experience" },
  { value: "98%",  label: "Client Satisfaction" },
];

const WHY_US = [
  {
    title: "ISO 9001 Certified Quality",
    desc: "Every product undergoes rigorous multi-stage inspection. Our factory is ISO 9001:2015 certified and regularly audited by SGS.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "Global Logistics Network",
    desc: "Reliable shipping to 40+ countries. Consolidation services, LCL/FCL options, and real-time order tracking for every shipment.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M6.115 5.19l.319 1.913A6 6 0 008.11 10.36L9.75 12l-.387.775c-.217.433-.132.956.21 1.298l1.348 1.348c.21.21.329.497.329.795v1.089c0 .426.24.815.622 1.006l.153.076c.433.217.956.132 1.298-.21l.723-.723a8.7 8.7 0 002.288-4.042 1.087 1.087 0 00-.358-1.099l-1.33-1.108c-.251-.21-.582-.299-.905-.245l-1.17.195a1.125 1.125 0 01-.98-.314l-.295-.295a1.125 1.125 0 010-1.591l.017-.017c.372-.372.596-.878.596-1.414 0-.523-.199-1.026-.554-1.403L9.62 5.498a1.875 1.875 0 00-2.346-.271l-1.16.58z" />
      </svg>
    ),
  },
  {
    title: "Custom OEM / ODM",
    desc: "From material specification to private-label packaging, we tailor solutions to your requirements — minimum order flexibility available.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
      </svg>
    ),
  },
  {
    title: "Dedicated Account Manager",
    desc: "Every client gets a dedicated bilingual account manager — fast response, proactive updates, and on-time quote delivery guaranteed.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
      </svg>
    ),
  },
  {
    title: "Rapid Sampling & Lead Times",
    desc: "Samples shipped within 3–5 business days. Mass production lead times consistently shorter than industry average.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
  {
    title: "Transparent Pricing",
    desc: "Itemised quotes with no hidden fees. Volume discounts, payment flexibility, and clear breakdown of tooling costs.",
    icon: (
      <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
  },
];

const TESTIMONIALS = [
  {
    quote: "We've sourced from NorthForge for 8 years. The quality consistency and on-time delivery are simply unmatched by any other supplier we've tried.",
    name: "Michael R.",
    role: "Procurement Director",
    company: "BuildPro USA",
    avatar: "MR",
  },
  {
    quote: "Their OEM service allowed us to launch a private-label product line in under 3 months. The account manager was responsive and professional throughout.",
    name: "Sophie L.",
    role: "Product Manager",
    company: "TechHaus GmbH",
    avatar: "SL",
  },
  {
    quote: "Certifications were comprehensively documented and the customs clearance process was smooth every time. Highly recommended for EU importers.",
    name: "Carlos M.",
    role: "Import Manager",
    company: "IndustrialES S.L.",
    avatar: "CM",
  },
];

export default async function HomePage() {
  const [categories, applicationsRes, certifications, heroCta, featuredProducts] = await Promise.all([
    getPublishedCategories(),
    getPublishedApplications(),
    getPublishedCertifications(),
    getCTAByKey("hero_home"),
    getFeaturedProducts(),
  ]);
  const applications = applicationsRes.data.slice(0, 6);

  return (
    <>
      <PageViewTracker pageType="home" />
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
              Trusted by buyers in 40+ countries
            </span>

            <h1 className="max-w-4xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
              {heroCta?.headline ?? (
                <>
                  Your Global Manufacturing
                  <br />
                  <span className="text-blue-300">Partner Since 2003</span>
                </>
              )}
            </h1>

            {heroCta?.subheadline ? (
              <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-blue-100">
                {heroCta.subheadline}
              </p>
            ) : (
              <p className="mx-auto mt-5 max-w-2xl text-lg leading-relaxed text-blue-100">
                ISO&nbsp;9001 certified precision hardware, fasteners, and industrial components — 
                delivered reliably to distributors and OEMs worldwide.
              </p>
            )}

            <div className="mt-9 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
              <Link
                href={heroCta?.button_url ?? "/products"}
                className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
              >
                {heroCta?.button_label ?? "Browse Products"}
              </Link>
              <Link
                href="/rfq"
                className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
              >
                Request a Quote →
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
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Our Top Products</h2>
              <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
                Industry-leading solutions trusted by buyers worldwide.
              </p>
            </div>

            <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {featuredProducts.map((product) => (
                <Link
                  key={product.id}
                  href={`/products/${product.slug}`}
                  className="group flex flex-col rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:border-blue-300 hover:shadow-md transition-all"
                >
                  <span className="mb-3 flex h-32 w-full items-center justify-center rounded-lg bg-blue-50 text-4xl group-hover:bg-blue-100 transition-colors">
                    ⬡
                  </span>
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
              <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
                From standard hardware to precision-engineered specials — browse our comprehensive product range.
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
              <h2 className="mt-2 text-3xl font-bold text-gray-900">Industry Applications</h2>
              <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
                Tailored solutions for key industrial sectors around the world.
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

      {/* ── Testimonials ── */}
      <section className="bg-white py-20">
        <div className="mx-auto max-w-6xl px-6">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-blue-600">
              Client Stories
            </span>
            <h2 className="mt-2 text-3xl font-bold text-gray-900">Trusted by Global Buyers</h2>
          </div>

          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {TESTIMONIALS.map((t) => (
              <div key={t.name} className="flex flex-col rounded-xl border border-gray-100 bg-gray-50 p-6">
                {/* Stars */}
                <div className="flex gap-0.5 text-amber-400">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <svg key={i} className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                    </svg>
                  ))}
                </div>
                <blockquote className="mt-3 flex-1 text-sm leading-relaxed text-gray-600">
                  &ldquo;{t.quote}&rdquo;
                </blockquote>
                <div className="mt-5 flex items-center gap-3">
                  <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">
                    {t.avatar}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{t.name}</p>
                    <p className="text-xs text-gray-500">
                      {t.role}, {t.company}
                    </p>
                  </div>
                </div>
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
              <p className="mx-auto mt-3 max-w-xl text-base text-gray-500">
                Internationally recognised compliance documentation ready for your procurement team.
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
          <h2 className="text-3xl font-bold">Ready to Source Smarter?</h2>
          <p className="mx-auto mt-4 max-w-xl text-lg text-blue-200 leading-relaxed">
            Get a detailed quote within 24 hours. No commitments — just fast, professional pricing
            from a team that understands international procurement.
          </p>
          <div className="mt-8 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
            <Link
              href="/rfq"
              className="rounded-xl bg-white px-8 py-3.5 text-sm font-bold text-blue-900 shadow-lg hover:bg-blue-50 transition-colors"
            >
              Get a Free Quote
            </Link>
            <Link
              href="/about"
              className="rounded-xl border border-white/30 bg-white/10 px-8 py-3.5 text-sm font-semibold text-white hover:bg-white/20 transition-colors"
            >
              Learn About {SITE_NAME}
            </Link>
          </div>
          <p className="mt-6 text-xs text-blue-400">
            Response within 1 business day · No spam, no cold calls
          </p>
        </div>
      </section>
    </>
  );
}
