"use client";

import { useLocale } from "next-intl";
import { Link } from "@/i18n/navigation";
import { useMessageNamespace } from "@/lib/messages";
import { resolveLocalizedText, type SiteConfig, type SiteFooterSection } from "@/lib/siteConfig";
import { BrandMark } from "@/components/ui/BrandMark";
import { rewriteLegacyPublicPath } from "@/lib/legacyPublicPaths";

type FooterMessages = {
  description: string;
  builtWithPrecision: string;
  allRightsReserved: string;
  certifications: string[];
  sections: {
    products: { heading: string; catalog: string; applications: string; rfq: string; custom: string };
    company: { heading: string; about: string; certifications: string; news: string; careers: string };
    support: { heading: string; faq: string; contact: string; docs: string; dealers: string };
    legal: { heading: string; privacy: string; terms: string; cookies: string };
  };
};

function getDefaultSections(copy: FooterMessages): SiteFooterSection[] {
  return [
    {
      heading: copy.sections.products.heading,
      items: [
        { href: "/products", label: copy.sections.products.catalog },
        { href: "/applications", label: copy.sections.products.applications },
        { href: "/rfq", label: copy.sections.products.rfq },
        { href: "/oem-odm", label: copy.sections.products.custom },
      ],
    },
    {
      heading: copy.sections.company.heading,
      items: [
        { href: "/about", label: copy.sections.company.about },
        { href: "/certifications", label: copy.sections.company.certifications },
        { href: "/news", label: copy.sections.company.news },
        { href: "/careers", label: copy.sections.company.careers },
      ],
    },
    {
      heading: copy.sections.support.heading,
      items: [
        { href: "/faq", label: copy.sections.support.faq },
        { href: "/contact", label: copy.sections.support.contact },
        { href: "/docs", label: copy.sections.support.docs },
        { href: "/dealers", label: copy.sections.support.dealers },
      ],
    },
    {
      heading: copy.sections.legal.heading,
      items: [
        { href: "/privacy", label: copy.sections.legal.privacy },
        { href: "/terms", label: copy.sections.legal.terms },
        { href: "/cookies", label: copy.sections.legal.cookies },
      ],
    },
  ];
}

export function Footer({ siteConfig }: { siteConfig: SiteConfig }) {
  const copy = useMessageNamespace<FooterMessages>("footer");
  const locale = useLocale();
  const siteName = siteConfig.brandName;
  const isTestScenario = Boolean(siteConfig.demoCompanyFolder);
  const year = new Date().getFullYear();
  const sections = siteConfig.footerSections?.length ? siteConfig.footerSections : getDefaultSections(copy);
  const badges = siteConfig.footerBadges?.length ? siteConfig.footerBadges : copy.certifications;

  return (
    <footer className="border-t border-gray-200 bg-gray-900 text-gray-400">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6 lg:px-8">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-6">
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-2">
              <BrandMark name={siteName} mark={siteConfig.logoMark} logoUrl={siteConfig.logoUrl} className="bg-blue-600 text-white" />
              <span className="text-base font-bold text-white">{siteName}</span>
            </Link>
            <p className="mt-3 text-sm leading-relaxed">{copy.description}</p>

            {isTestScenario ? (
              <p className="mt-5 max-w-sm text-sm leading-relaxed text-amber-200">{locale === "zh-TW" ? "這是 ForgeBase 功能測試情境；不提供 NorthForge 業務聯繫、報價或供貨服務。" : "This is a ForgeBase functional test scenario; NorthForge does not provide sales contact, quotations, or supply service."}</p>
            ) : (
              <ul className="mt-5 space-y-1.5 text-sm">
                <li className="flex items-center gap-2">
                  <svg className="h-4 w-4 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
                  </svg>
                  {siteConfig.contactEmail}
                </li>
                <li className="flex items-center gap-2">
                  <svg className="h-4 w-4 shrink-0 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" />
                  </svg>
                  {siteConfig.contactPhone}
                </li>
              </ul>
            )}

            {siteConfig.socialLinks?.length ? (
              <div className="mt-5 flex items-center gap-3">
                {siteConfig.socialLinks.map((social) => (
                <a
                  key={`${social.href}-${String(social.label)}`}
                  href={social.href}
                  aria-label={resolveLocalizedText(social.label, locale, social.href)}
                  className="flex h-8 w-8 items-center justify-center rounded-md bg-gray-800 text-gray-400 transition-colors hover:bg-blue-700 hover:text-white"
                >
                  <span className="text-[10px] font-bold uppercase">{resolveLocalizedText(social.label, locale, "Link").slice(0, 2)}</span>
                </a>
                ))}
              </div>
            ) : null}
          </div>

          {sections.map((section) => (
            <div key={resolveLocalizedText(section.heading, locale, "section")}>
              <h3 className="text-xs font-semibold uppercase tracking-widest text-gray-300">
                {resolveLocalizedText(section.heading, locale, "Section")}
              </h3>
              <ul className="mt-4 space-y-2">
                {section.items.map((item) => {
                  const href = rewriteLegacyPublicPath(item.href);
                  return (
                  <li key={href}>
                    <Link href={href} className="text-sm transition-colors hover:text-white">
                      {resolveLocalizedText(item.label, locale, href)}
                    </Link>
                  </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 flex flex-wrap items-center gap-3 border-t border-gray-800 pt-8">
          {badges.map((cert, index) => (
            <span
              key={`${index}-${String(cert)}`}
              className="rounded-full border border-gray-700 px-3 py-1 text-xs font-medium text-gray-400"
            >
              {resolveLocalizedText(cert, locale, "Badge")}
            </span>
          ))}
        </div>

        <div className="mt-6 flex flex-col items-center justify-between gap-2 border-t border-gray-800 pt-6 sm:flex-row">
          <p className="text-xs text-gray-500">
            © {year} {siteName}. {copy.allRightsReserved}
          </p>
          <p className="text-xs text-gray-600">{copy.builtWithPrecision}</p>
        </div>
      </div>
    </footer>
  );
}
