"use client";

import { useEffect, useState } from "react";
import NextLink from "next/link";
import { useLocale } from "next-intl";
import { Crosshair, Menu, X, ArrowUpRight } from "lucide-react";
import { usePathname } from "@/i18n/navigation";
import { useMessageNamespace } from "@/lib/messages";
import { resolveLocalizedText, type SiteConfig, type SiteNavItem } from "@/lib/siteConfig";
import { localizedPath } from "@/lib/localizedPath";
import { LanguageSwitcher } from "@/components/layout/LanguageSwitcher";

type HeaderMessages = {
  rfq: string;
  openMenu: string;
  navigationLabel: string;
  precisionDemo: string;
  nav: { products: string; applications: string; certifications: string; about: string; contact: string };
};

function defaults(copy: HeaderMessages): SiteNavItem[] {
  return [
    { href: "/products", label: copy.nav.products },
    { href: "/applications", label: copy.nav.applications },
    { href: "/certifications", label: copy.nav.certifications },
    { href: "/about", label: copy.nav.about },
    { href: "/contact", label: copy.nav.contact },
  ];
}

export function PrecisionHeader({ siteConfig }: { siteConfig: SiteConfig }) {
  const locale = useLocale();
  const pathname = usePathname();
  const copy = useMessageNamespace<HeaderMessages>("header");
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [pathname]);
  const nav = siteConfig.headerNav?.length ? siteConfig.headerNav : defaults(copy);
  const action = siteConfig.headerActions?.[0] ?? { href: "/rfq", label: copy.rfq };

  return (
    <header className="sticky top-0 z-40 border-b border-white/10 bg-[#0b1013]/95 text-white backdrop-blur">
      <div className="mx-auto flex h-20 max-w-[1440px] items-center justify-between px-5 lg:px-10">
        <NextLink href={localizedPath(locale, "/")} className="flex items-center gap-3" aria-label={siteConfig.brandName}>
          {siteConfig.logoUrl ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={siteConfig.logoUrl} alt={siteConfig.brandName} className="h-10 w-auto max-w-28 object-contain" />
          ) : (
            <span className="grid h-10 w-10 place-items-center border border-lime-300/70 text-lime-300"><Crosshair size={22} /></span>
          )}
          <span className="text-base font-black uppercase tracking-[0.12em]">{siteConfig.brandName}<small className="block text-[9px] font-semibold tracking-[0.28em] text-gray-500">{copy.precisionDemo}</small></span>
        </NextLink>
        <nav className="hidden items-center gap-7 lg:flex" aria-label={copy.navigationLabel}>
          {nav.map((item) => <NextLink key={item.href} href={localizedPath(locale, item.href)} className="text-[11px] font-bold uppercase tracking-[0.14em] text-gray-300 hover:text-lime-300">{resolveLocalizedText(item.label, locale)}</NextLink>)}
          <NextLink href={localizedPath(locale, action.href)} className="inline-flex items-center gap-2 bg-lime-300 px-5 py-3 text-[11px] font-black uppercase tracking-[0.12em] text-black hover:bg-lime-200">{resolveLocalizedText(action.label, locale)}<ArrowUpRight size={15} /></NextLink>
          <LanguageSwitcher className="text-gray-300" />
        </nav>
        <button type="button" onClick={() => setOpen(!open)} className="grid h-10 w-10 place-items-center border border-white/20 lg:hidden" aria-label={copy.openMenu} aria-expanded={open}>{open ? <X /> : <Menu />}</button>
      </div>
      {open && <nav className="grid border-t border-white/10 bg-[#0b1013] px-5 py-5 lg:hidden" aria-label={copy.navigationLabel}>{nav.map((item) => <NextLink key={item.href} href={localizedPath(locale, item.href)} className="border-b border-white/10 py-4 text-sm font-bold uppercase tracking-wider">{resolveLocalizedText(item.label, locale)}</NextLink>)}<LanguageSwitcher className="mt-4 text-gray-300" /><NextLink href={localizedPath(locale, action.href)} className="mt-5 bg-lime-300 px-5 py-4 text-center text-sm font-black uppercase text-black">{resolveLocalizedText(action.label, locale)}</NextLink></nav>}
    </header>
  );
}
