import Link from "next/link";

const FOOTER_LINKS = [
  {
    heading: "Products",
    items: [
      { label: "Product Catalog",   href: "/products" },
      { label: "By Application",    href: "/applications" },
      { label: "Request a Quote",   href: "/rfq" },
      { label: "Custom Solutions",  href: "/contact" },
    ],
  },
  {
    heading: "Company",
    items: [
      { label: "About Us",          href: "/about" },
      { label: "Certifications",    href: "/certifications" },
      { label: "News & Updates",    href: "/news" },
      { label: "Careers",           href: "/careers" },
    ],
  },
  {
    heading: "Support",
    items: [
      { label: "FAQ",               href: "/faq" },
      { label: "Contact Us",        href: "/contact" },
      { label: "Technical Docs",    href: "/docs" },
      { label: "Dealer Locator",    href: "/dealers" },
    ],
  },
  {
    heading: "Legal",
    items: [
      { label: "Privacy Policy",    href: "/privacy" },
      { label: "Terms of Service",  href: "/terms" },
      { label: "Cookie Policy",     href: "/cookies" },
    ],
  },
];

const SOCIAL_LINKS = [
  {
    label: "LinkedIn",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M16 8a6 6 0 016 6v7h-4v-7a2 2 0 00-2-2 2 2 0 00-2 2v7h-4v-7a6 6 0 016-6zM2 9h4v12H2z" />
        <circle cx="4" cy="4" r="2" />
      </svg>
    ),
  },
  {
    label: "X / Twitter",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
      </svg>
    ),
  },
  {
    label: "YouTube",
    href: "#",
    icon: (
      <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24">
        <path d="M23.498 6.186a3.016 3.016 0 00-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 00.502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 002.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 002.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z" />
      </svg>
    ),
  },
];

export function Footer() {
  const siteName = process.env.NEXT_PUBLIC_SITE_NAME || "ForgeBase";
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-gray-200 bg-gray-900 text-gray-400">
      {/* Main grid */}
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-6">
          {/* Brand — spans 2 cols on lg */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-[11px] font-bold text-white">
                NF
              </div>
              <span className="text-base font-bold text-white">{siteName}</span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed">
              Precision manufacturing solutions trusted by industrial buyers in
              40+ countries. ISO&nbsp;9001 certified, 20+ years of experience.
            </p>

            {/* Contact snippet */}
            <ul className="mt-5 space-y-1.5 text-sm">
              <li className="flex items-center gap-2">
                <svg className="h-4 w-4 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                </svg>
                sales@northforge-tools.com
              </li>
              <li className="flex items-center gap-2">
                <svg className="h-4 w-4 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                </svg>
                +886-6-259-1000
              </li>
            </ul>

            {/* Social icons */}
            <div className="mt-5 flex items-center gap-3">
              {SOCIAL_LINKS.map((s) => (
                <a
                  key={s.label}
                  href={s.href}
                  aria-label={s.label}
                  className="flex h-8 w-8 items-center justify-center rounded-md bg-gray-800 text-gray-400 hover:bg-blue-700 hover:text-white transition-colors"
                >
                  {s.icon}
                </a>
              ))}
            </div>
          </div>

          {/* Link columns */}
          {FOOTER_LINKS.map((section) => (
            <div key={section.heading}>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300">
                {section.heading}
              </h3>
              <ul className="mt-4 space-y-2">
                {section.items.map((item) => (
                  <li key={item.href}>
                    <Link
                      href={item.href}
                      className="text-sm transition-colors hover:text-white"
                    >
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Certifications strip */}
        <div className="mt-10 flex flex-wrap items-center gap-3 border-t border-gray-800 pt-8">
          {["ISO 9001:2015", "CE Certified", "RoHS Compliant", "SGS Audited"].map((cert) => (
            <span
              key={cert}
              className="rounded-full border border-gray-700 px-3 py-1 text-xs font-medium text-gray-400"
            >
              {cert}
            </span>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-6 flex flex-col items-center justify-between gap-2 border-t border-gray-800 pt-6 sm:flex-row">
          <p className="text-xs text-gray-500">
            © {year} {siteName}. All rights reserved.
          </p>
          <p className="text-xs text-gray-600">
            Built with precision · Designed for growth
          </p>
        </div>
      </div>
    </footer>
  );
}
