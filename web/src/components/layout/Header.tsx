"use client";
import { useState, useEffect } from "react";
import NextLink from "next/link";
import { useLocale } from "next-intl";
import { Link, usePathname } from "@/i18n/navigation";
import { Menu, Phone, FileText, Globe } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { useMessageNamespace } from "@/lib/messages";
import { cn } from "@/lib/utils";

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

export function Header() {
  const pathname = usePathname();
  const locale = useLocale();
  const copy = useMessageNamespace<HeaderMessages>("header");
  const [sheetOpen, setSheetOpen] = useState(false);
  const [scrolled, setScrolled]   = useState(false);
  const localizedPath = pathname === "/" ? "" : pathname;
  const localeSwitchHref = locale === "en"
    ? `/zh-TW${localizedPath}`
    : (localizedPath || "/");

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => { setSheetOpen(false); }, [pathname]);

  const siteName = process.env.NEXT_PUBLIC_SITE_NAME === "ForgeBase"
    ? "NorthForge Tools"
    : (process.env.NEXT_PUBLIC_SITE_NAME || "NorthForge Tools");

  return (
    <header
      className={cn(
        "sticky top-0 z-40 border-b transition-all duration-200",
        scrolled
          ? "border-border/80 bg-background/95 shadow-sm backdrop-blur-md"
          : "border-transparent bg-background"
      )}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* ─── Logo ─── */}
        <Link href="/" className="group flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-[11px] font-bold text-primary-foreground transition-all group-hover:scale-105 group-hover:shadow-md">
            NF
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-lg font-bold tracking-tight text-foreground group-hover:text-primary transition-colors">
              {siteName}
            </span>
            <Badge variant="outline" className="hidden h-4 px-1.5 text-[9px] font-medium uppercase tracking-wider sm:flex">
              B2B
            </Badge>
          </div>
        </Link>

        {/* ─── Desktop nav ─── */}
        <nav className="hidden items-center gap-0.5 md:flex">
          {NAV_ITEMS.map((link) => {
            const active = pathname === link.href || pathname.startsWith(link.href + "/");
            return (
              <Link
                key={link.href}
                href={link.href}
                className={cn(
                  "relative rounded-md px-3.5 py-2 text-sm font-medium transition-colors",
                  active
                    ? "text-primary"
                    : "text-muted-foreground hover:text-foreground"
                )}
              >
                {copy.nav[link.key]}
                {active && (
                  <span className="absolute bottom-0 left-1/2 h-0.5 w-4 -translate-x-1/2 rounded-full bg-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* ─── Desktop CTAs ─── */}
        <div className="hidden items-center gap-2 md:flex">
          {/* Language switcher */}
          <Button variant="ghost" size="sm" asChild className="gap-1 text-muted-foreground hover:text-foreground px-2">
            <NextLink href={localeSwitchHref} hrefLang={locale === "en" ? "zh-TW" : "en"}>
              <Globe className="h-3.5 w-3.5" />
              {copy.langSwitch}
            </NextLink>
          </Button>
          <Button variant="ghost" size="sm" asChild className="gap-1.5 text-muted-foreground hover:text-foreground">
            <Link href="/rfq">
              <FileText className="h-3.5 w-3.5" />
              {copy.rfq}
            </Link>
          </Button>
          <Button size="sm" asChild className="gap-1.5 shadow-sm">
            <Link href="/contact">
              <Phone className="h-3.5 w-3.5" />
              {copy.contact}
            </Link>
          </Button>
        </div>

        {/* ─── Mobile hamburger ─── */}
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden h-9 w-9"
          aria-label={copy.openMenu}
          onClick={() => setSheetOpen(true)}
        >
          <Menu className="h-5 w-5" />
        </Button>
      </div>

      {/* ─── Mobile Sheet ─── */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right" className="w-[300px] p-0">
          <SheetHeader className="flex flex-row items-center gap-3 border-b px-5 py-4">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-[10px] font-bold text-primary-foreground">
              NF
            </div>
            <SheetTitle className="text-sm font-semibold">{siteName}</SheetTitle>
          </SheetHeader>

          <nav className="px-3 py-4">
            <div className="space-y-0.5">
              {NAV_ITEMS.map((link) => {
                const active = pathname === link.href || pathname.startsWith(link.href + "/");
                return (
                  <Link
                    key={link.href}
                    href={link.href}
                    className={cn(
                      "flex items-center rounded-md px-4 py-2.5 text-sm font-medium transition-colors",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-foreground hover:bg-muted"
                    )}
                  >
                    {copy.nav[link.key]}
                    {active && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />}
                  </Link>
                );
              })}
            </div>

            <Separator className="my-4" />

            <div className="space-y-2 px-1">
              <Button variant="outline" className="w-full justify-start gap-2" asChild>
                <Link href="/rfq">
                  <FileText className="h-4 w-4" />
                  {copy.submitRfq}
                </Link>
              </Button>
              <Button className="w-full justify-start gap-2" asChild>
                <Link href="/contact">
                  <Phone className="h-4 w-4" />
                  {copy.contact}
                </Link>
              </Button>
            </div>

            <div className="mt-6 rounded-lg bg-muted p-4">
              <p className="text-xs font-semibold text-foreground">{copy.partnerTitle}</p>
              <p className="mt-1 text-xs text-muted-foreground">{copy.partnerDescription}</p>
            </div>
          </nav>
        </SheetContent>
      </Sheet>
    </header>
  );
}
