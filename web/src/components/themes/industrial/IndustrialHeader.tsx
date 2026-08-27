"use client";
import { useState, useEffect } from "react";
import NextLink from "next/link";
import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { Menu, X, Globe, ArrowRight } from "lucide-react";
import { useMessageNamespace } from "@/lib/messages";
import { resolveLocalizedText, type SiteAction, type SiteConfig, type SiteNavItem } from "@/lib/siteConfig";
import { cn } from "@/lib/utils";
import { BrandMark } from "@/components/ui/BrandMark";

type HeaderMessages = {
  rfq: string;
  submitRfq: string;
  contact: string;
  openMenu: string;
  partnerTitle: string;
  partnerDescription: string;
  langSwitch: string;
  nav: {
    products: string;
    applications: string;
    certifications: string;
    about: string;
    contact: string;
  };
};

const NAV_ITEMS: Array<{ href: string; key: keyof HeaderMessages["nav"] }> = [
  { href: "/products", key: "products" },
  { href: "/applications", key: "applications" },
  { href: "/certifications", key: "certifications" },
  { href: "/about", key: "about" },
  { href: "/contact", key: "contact" },
];

function getDefaultNav(copy: HeaderMessages): SiteNavItem[] {
  return NAV_ITEMS.map((item) => ({ href: item.href, label: copy.nav[item.key] }));
}

function getDefaultActions(copy: HeaderMessages): SiteAction[] {
  return [{ href: "/rfq", label: copy.rfq }];
}

/**
 * Industrial header: dark background, bold typography, angled accent.
 * Contrasts with the cobalt classic header (white bg, rounded elements).
 */
export function IndustrialHeader({ siteConfig }: { siteConfig: SiteConfig }) {
  const pathname = usePathname();
  const locale = useLocale();
  const copy = useMessageNamespace<HeaderMessages>("header");
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const localizedPath = pathname === "/" ? "" : pathname;
  const localeSwitchHref = locale === "en"
    ? `/zh-TW${localizedPath}`
    : (localizedPath || "/");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => { setMenuOpen(false); }, [pathname]);

  const siteName = siteConfig.brandName;
  const isTestScenario = Boolean(siteConfig.demoCompanyFolder);
  const navItems = siteConfig.headerNav?.length ? siteConfig.headerNav : getDefaultNav(copy);
  const actions = siteConfig.headerActions?.length ? siteConfig.headerActions : getDefaultActions(copy);
  const primaryAction = actions[0];

  return (
    <>
      {/* ─── Top utility bar ─── */}
      <div className="bg-gray-950 text-gray-400 text-xs">
        <div className="mx-auto flex h-8 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <span>{isTestScenario ? (locale === "zh-TW" ? "ForgeBase 功能測試網站・不提供業務聯繫" : "ForgeBase functional test site · no sales contact") : `${siteConfig.contactEmail} | ${siteConfig.contactPhone}`}</span>
          <NextLink
            href={localeSwitchHref}
            hrefLang={locale === "en" ? "zh-TW" : "en"}
            className="flex items-center gap-1 hover:text-white transition-colors"
            onClick={(event) => {
              if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
                return;
              }
              // Keep the root-level next-intl provider in sync when changing locale.
              // NextLink supplies basePath; a full navigation rebuilds the root layout.
              event.preventDefault();
              window.location.assign(event.currentTarget.href);
            }}
          >
            <Globe className="h-3 w-3" />
            {copy.langSwitch}
          </NextLink>
        </div>
      </div>

      {/* ─── Main header ─── */}
      <header
        className={cn(
          "sticky top-0 z-40 transition-all duration-200",
          scrolled
            ? "bg-gray-900/98 shadow-lg backdrop-blur-sm"
            : "bg-gray-900"
        )}
      >
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          {/* ─── Logo ─── */}
          <Link href="/" className="group flex items-center gap-3">
            <BrandMark name={siteName} mark={siteConfig.logoMark} logoUrl={siteConfig.logoUrl} className="h-9 w-9 text-sm font-black skew-x-[-3deg]" imageClassName="h-9" />
            <div className="flex flex-col leading-none">
              <span className="text-sm font-black uppercase tracking-[0.15em] text-white">
                {siteName}
              </span>
              <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-gray-500">
                {isTestScenario ? (locale === "zh-TW" ? "功能測試情境" : "Functional test") : (locale === "zh-TW" ? "專業製造" : "Manufacturing")}
              </span>
            </div>
          </Link>

          {/* ─── Desktop nav ─── */}
          <nav className="hidden items-center gap-0 md:flex">
            {navItems.map((link) => {
              const active = pathname === link.href || pathname.startsWith(link.href + "/");
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "relative px-4 py-4 text-xs font-bold uppercase tracking-widest transition-colors",
                    active
                      ? "text-primary"
                      : "text-gray-400 hover:text-white"
                  )}
                >
                  {resolveLocalizedText(link.label, locale, link.href)}
                  {active && (
                    <span className="absolute bottom-0 left-0 right-0 h-[3px] bg-primary" />
                  )}
                </Link>
              );
            })}
          </nav>

          {/* ─── Desktop CTA ─── */}
          <div className="hidden items-center gap-3 md:flex">
            <Link
              href={primaryAction?.href ?? "/rfq"}
              className="flex items-center gap-1.5 bg-primary px-5 py-2 text-xs font-black uppercase tracking-wider text-primary-foreground skew-x-[-3deg] hover:brightness-110 transition-all"
            >
              <span className="skew-x-[3deg]">{resolveLocalizedText(primaryAction?.label, locale, copy.rfq)}</span>
              <ArrowRight className="h-3.5 w-3.5 skew-x-[3deg]" />
            </Link>
          </div>

          {/* ─── Mobile hamburger ─── */}
          <button
            className="flex h-10 w-10 items-center justify-center text-gray-400 hover:text-white md:hidden"
            aria-label={copy.openMenu}
            onClick={() => setMenuOpen(!menuOpen)}
          >
            {menuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>

        {/* ─── Mobile overlay menu ─── */}
        {menuOpen && (
          <div className="absolute left-0 right-0 top-full z-50 border-t border-gray-800 bg-gray-900 md:hidden">
            <nav className="mx-auto max-w-7xl px-4 py-4">
              {navItems.map((link) => {
                const active = pathname === link.href || pathname.startsWith(link.href + "/");
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      "block border-b border-gray-800 px-2 py-3 text-sm font-bold uppercase tracking-wider",
                      active ? "text-primary" : "text-gray-300"
                    )}
                  >
                    {resolveLocalizedText(link.label, locale, link.href)}
                  </Link>
                );
              })}
              <Link
                href={primaryAction?.href ?? "/rfq"}
                className="mt-4 flex items-center justify-center gap-2 bg-primary px-5 py-3 text-sm font-black uppercase tracking-wider text-primary-foreground"
              >
                {resolveLocalizedText(primaryAction?.label, locale, copy.rfq)}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </nav>
          </div>
        )}
      </header>
    </>
  );
}
