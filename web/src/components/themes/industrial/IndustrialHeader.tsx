"use client";
import { useState, useEffect } from "react";
import NextLink from "next/link";
import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { Menu, X, Globe, ArrowRight } from "lucide-react";
import { useMessageNamespace } from "@/lib/messages";
import { cn } from "@/lib/utils";
import { siteConfig } from "@/lib/siteConfig";

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

/**
 * Industrial header: dark background, bold typography, angled accent.
 * Contrasts with the cobalt classic header (white bg, rounded elements).
 */
export function IndustrialHeader() {
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

  return (
    <>
      {/* ─── Top utility bar ─── */}
      <div className="bg-gray-950 text-gray-400 text-xs">
        <div className="mx-auto flex h-8 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <span>{siteConfig.contactEmail} &nbsp;|&nbsp; {siteConfig.contactPhone}</span>
          <NextLink
            href={localeSwitchHref}
            hrefLang={locale === "en" ? "zh-TW" : "en"}
            className="flex items-center gap-1 hover:text-white transition-colors"
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
            <div className="flex h-9 w-9 items-center justify-center bg-primary text-sm font-black text-primary-foreground skew-x-[-3deg]">
              {siteConfig.logoMark}
            </div>
            <div className="flex flex-col leading-none">
              <span className="text-sm font-black uppercase tracking-[0.15em] text-white">
                {siteName}
              </span>
              <span className="text-[9px] font-medium uppercase tracking-[0.2em] text-gray-500">
                Manufacturing
              </span>
            </div>
          </Link>

          {/* ─── Desktop nav ─── */}
          <nav className="hidden items-center gap-0 md:flex">
            {NAV_ITEMS.map((link) => {
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
                  {copy.nav[link.key]}
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
              href="/rfq"
              className="flex items-center gap-1.5 bg-primary px-5 py-2 text-xs font-black uppercase tracking-wider text-primary-foreground skew-x-[-3deg] hover:brightness-110 transition-all"
            >
              <span className="skew-x-[3deg]">{copy.rfq}</span>
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
              {NAV_ITEMS.map((link) => {
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
                    {copy.nav[link.key]}
                  </Link>
                );
              })}
              <Link
                href="/rfq"
                className="mt-4 flex items-center justify-center gap-2 bg-primary px-5 py-3 text-sm font-black uppercase tracking-wider text-primary-foreground"
              >
                {copy.rfq}
                <ArrowRight className="h-4 w-4" />
              </Link>
            </nav>
          </div>
        )}
      </header>
    </>
  );
}
