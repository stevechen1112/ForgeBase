import Link from "next/link";
import type { Metadata } from "next";
import { StructuredData, buildBreadcrumbSchema } from "@/components/seo/StructuredData";
import { ContactForm } from "@/components/forms/ContactForm";
import { PageViewTracker } from "@/components/tracking/PageViewTracker";

export const metadata: Metadata = {
  title: "Contact Us",
  description:
    "Get in touch with our team to discuss your requirements, request a quote, or ask about our products.",
};

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://example.com";

const OFFICES = [
  {
    city: "Taipei HQ",
    address: "12F, No. 88, Xinyi Road, Xinyi District, Taipei 110",
    phone: "+886-2-1234-5678",
    hours: "Mon–Fri 09:00–18:00 CST",
  },
  {
    city: "Shenzhen Factory",
    address: "Building B, Longhua Science Park, Shenzhen 518109",
    phone: "+86-755-8888-9999",
    hours: "Mon–Sat 08:30–17:30 CST",
  },
];

const REASONS = [
  { label: "Product Enquiry",   desc: "Pricing, MOQ, lead times" },
  { label: "OEM / ODM Service", desc: "Custom design & private label" },
  { label: "Technical Support", desc: "Specs, data sheets, standards" },
  { label: "Partnership",       desc: "Distributors & agents welcome" },
];

export default function ContactPage() {
  const contactEmail = process.env.NEXT_PUBLIC_CONTACT_EMAIL || "sales@forgebase.com";
  const contactPhone = process.env.NEXT_PUBLIC_CONTACT_PHONE || "+886-2-1234-5678";

  return (
    <>
      <StructuredData
        data={buildBreadcrumbSchema([
          { name: "Home", url: SITE_URL },
          { name: "Contact", url: `${SITE_URL}/contact` },
        ])}
      />
      <PageViewTracker pageType="contact" />

      {/* ── Hero header ── */}
      <section className="border-b border-gray-100 bg-gradient-to-br from-blue-950 to-blue-800 py-16 text-white">
        <div className="mx-auto max-w-6xl px-6">
          <nav aria-label="Breadcrumb" className="mb-4 text-xs text-blue-300">
            <Link href="/" className="hover:underline">Home</Link>
            <span className="mx-1.5">/</span>
            <span>Contact</span>
          </nav>
          <h1 className="text-4xl font-extrabold">Get in Touch</h1>
          <p className="mt-3 max-w-xl text-lg text-blue-200 leading-relaxed">
            Questions about products, pricing, or partnerships? Our sales team responds
            within&nbsp;1 business day.
          </p>

          {/* Quick contact chips */}
          <div className="mt-6 flex flex-wrap gap-3">
            <a
              href={`mailto:${contactEmail}`}
              className="flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-2 text-sm text-blue-100 hover:bg-blue-700/50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
              </svg>
              {contactEmail}
            </a>
            <a
              href={`tel:${contactPhone.replace(/\D/g, "")}`}
              className="flex items-center gap-2 rounded-full border border-blue-400/30 bg-blue-800/40 px-4 py-2 text-sm text-blue-100 hover:bg-blue-700/50 transition-colors"
            >
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
              </svg>
              {contactPhone}
            </a>
          </div>
        </div>
      </section>

      {/* ── Main content ── */}
      <section className="py-16">
        <div className="mx-auto max-w-6xl px-6">
          <div className="grid gap-12 lg:grid-cols-5">

            {/* Left column (info) */}
            <div className="lg:col-span-2 space-y-8">

              {/* Why contact us */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">How Can We Help?</h2>
                <ul className="mt-4 space-y-3">
                  {REASONS.map((r) => (
                    <li key={r.label} className="flex items-start gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3">
                      <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-blue-100 text-blue-700">
                        <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                        </svg>
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{r.label}</p>
                        <p className="text-xs text-gray-500">{r.desc}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Offices */}
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Our Offices</h2>
                <div className="mt-4 space-y-4">
                  {OFFICES.map((office) => (
                    <div key={office.city} className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
                      <h3 className="text-sm font-bold text-blue-700">{office.city}</h3>
                      <dl className="mt-2 space-y-1 text-sm text-gray-600">
                        <div className="flex items-start gap-2">
                          <svg className="mt-0.5 h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1115 0z" />
                          </svg>
                          <span>{office.address}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                          </svg>
                          <span>{office.phone}</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <svg className="h-4 w-4 shrink-0 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>{office.hours}</span>
                        </div>
                      </dl>
                    </div>
                  ))}
                </div>
              </div>

              {/* Response promise */}
              <div className="rounded-xl bg-blue-50 border border-blue-100 p-4">
                <div className="flex items-center gap-2">
                  <svg className="h-5 w-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-sm font-semibold text-blue-800">Response Guarantee</span>
                </div>
                <p className="mt-2 text-xs text-blue-700 leading-relaxed">
                  Every enquiry is acknowledged within 4 hours (business hours). Full response and
                  quote within 1 business day — guaranteed.
                </p>
              </div>

            </div>

            {/* Right column (form) */}
            <div className="lg:col-span-3">
              <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
                <h2 className="mb-1 text-xl font-bold text-gray-900">Send an Enquiry</h2>
                <p className="mb-6 text-sm text-gray-500">
                  Fill in the form below. All fields marked * are required.
                </p>
                <ContactForm />
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* ── Quick links ── */}
      <section className="border-t border-gray-100 bg-gray-50 py-12">
        <div className="mx-auto max-w-6xl px-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <p className="text-sm font-medium text-gray-700">
              Looking for something specific?
            </p>
            <div className="flex flex-wrap gap-3">
              <Link href="/products" className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors">
                Browse Products
              </Link>
              <Link href="/certifications" className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors">
                Certifications
              </Link>
              <Link href="/rfq" className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 transition-colors">
                Request a Quote
              </Link>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}


