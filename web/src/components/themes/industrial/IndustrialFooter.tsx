"use client";

import { Link } from "@/i18n/navigation";
import { useMessageNamespace } from "@/lib/messages";
import { siteConfig } from "@/lib/siteConfig";
import { ArrowRight } from "lucide-react";

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

/**
 * Industrial footer: full-dark with angular CTA banner, compact grid.
 * Contrasts with cobalt's lighter grey footer with rounded social icons.
 */
export function IndustrialFooter() {
  const copy = useMessageNamespace<FooterMessages>("footer");
  const siteName = siteConfig.brandName;
  const year = new Date().getFullYear();

  const linkGroups = [
    { heading: copy.sections.products.heading, items: [
      { href: "/products", label: copy.sections.products.catalog },
      { href: "/applications", label: copy.sections.products.applications },
      { href: "/rfq", label: copy.sections.products.rfq },
    ]},
    { heading: copy.sections.company.heading, items: [
      { href: "/about", label: copy.sections.company.about },
      { href: "/certifications", label: copy.sections.company.certifications },
      { href: "/careers", label: copy.sections.company.careers },
    ]},
    { heading: copy.sections.support.heading, items: [
      { href: "/faq", label: copy.sections.support.faq },
      { href: "/contact", label: copy.sections.support.contact },
      { href: "/docs", label: copy.sections.support.docs },
    ]},
  ];

  return (
    <footer className="bg-gray-950 text-gray-400">
      {/* ─── Angular CTA strip ─── */}
      <div className="relative overflow-hidden bg-primary">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage: "repeating-linear-gradient(135deg, transparent, transparent 20px, rgba(0,0,0,0.1) 20px, rgba(0,0,0,0.1) 40px)",
          }}
        />
        <div className="relative mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-sm font-black uppercase tracking-wider text-primary-foreground">
              Ready to start your tool program?
            </p>
            <p className="mt-0.5 text-xs text-primary-foreground/70">
              Get a quote within 24 hours for qualified enquiries.
            </p>
          </div>
          <Link
            href="/rfq"
            className="flex items-center gap-2 bg-gray-950 px-6 py-2.5 text-xs font-black uppercase tracking-wider text-white skew-x-[-3deg] hover:bg-gray-800 transition-colors"
          >
            <span className="skew-x-[3deg]">Request Quote</span>
            <ArrowRight className="h-3.5 w-3.5 skew-x-[3deg]" />
          </Link>
        </div>
      </div>

      {/* ─── Main footer grid ─── */}
      <div className="mx-auto max-w-7xl px-6 py-12">
        <div className="grid gap-10 sm:grid-cols-2 lg:grid-cols-5">
          {/* Brand column */}
          <div className="lg:col-span-2">
            <Link href="/" className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center bg-primary text-sm font-black text-primary-foreground skew-x-[-3deg]">
                {siteConfig.logoMark}
              </div>
              <span className="text-lg font-black uppercase tracking-widest text-white">
                {siteName}
              </span>
            </Link>
            <p className="mt-4 max-w-sm text-sm leading-relaxed">{copy.description}</p>
            <div className="mt-5 space-y-2 text-sm">
              <p className="text-white">{siteConfig.contactEmail}</p>
              <p>{siteConfig.contactPhone}</p>
            </div>
          </div>

          {/* Link columns */}
          {linkGroups.map((group) => (
            <div key={group.heading}>
              <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-primary">
                {group.heading}
              </h3>
              <ul className="mt-4 space-y-2.5">
                {group.items.map((item) => (
                  <li key={item.href}>
                    <Link href={item.href} className="text-sm transition-colors hover:text-white">
                      {item.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Certification badges */}
        <div className="mt-10 flex flex-wrap items-center gap-2 border-t border-gray-800 pt-8">
          {copy.certifications.map((cert) => (
            <span
              key={cert}
              className="bg-gray-900 px-3 py-1 text-[10px] font-bold uppercase tracking-wider text-gray-500"
            >
              {cert}
            </span>
          ))}
        </div>

        {/* Bottom bar */}
        <div className="mt-6 flex flex-col items-center justify-between gap-2 border-t border-gray-800 pt-6 sm:flex-row">
          <p className="text-xs text-gray-600">
            © {year} {siteName}. {copy.allRightsReserved}
          </p>
          <div className="flex gap-4 text-xs text-gray-600">
            <Link href="/privacy" className="hover:text-gray-400">{copy.sections.legal.privacy}</Link>
            <Link href="/terms" className="hover:text-gray-400">{copy.sections.legal.terms}</Link>
            <Link href="/cookies" className="hover:text-gray-400">{copy.sections.legal.cookies}</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
