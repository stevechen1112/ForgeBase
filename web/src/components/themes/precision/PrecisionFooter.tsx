import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { getLocale } from "next-intl/server";
import { BrandMark } from "@/components/ui/BrandMark";
import { localizedPath } from "@/lib/localizedPath";
import { rewriteLegacyPublicPath } from "@/lib/legacyPublicPaths";
import { resolveLocalizedText, type SiteConfig } from "@/lib/siteConfig";

export async function PrecisionFooter({ siteConfig }: { siteConfig: SiteConfig }) {
  const locale = await getLocale();
  const links = siteConfig.footerSections?.flatMap((section) => section.items).slice(0, 6) ?? [
    { href: "/products", label: "Parts" }, { href: "/applications", label: "Industries" },
    { href: "/certifications", label: "Quality" }, { href: "/about", label: "About" },
  ];
  return (
    <footer className="border-t border-white/10 bg-[#080c0e] text-gray-400">
      <div className="mx-auto grid max-w-[1440px] gap-10 px-6 py-12 md:grid-cols-[1.2fr_1fr_auto] lg:px-10">
        <div><div className="flex items-center gap-3 text-white"><BrandMark name={siteConfig.brandName} mark={siteConfig.logoMark} logoUrl={siteConfig.logoUrl} className="h-10 w-10 bg-lime-300 text-sm font-black text-black" imageClassName="h-10" /><strong className="uppercase tracking-[0.12em]">{siteConfig.brandName}</strong></div><p className="mt-4 max-w-md text-sm leading-6">Connected ForgeBase demonstration tenant. Company, parts, capabilities and credentials are fictional test content.</p></div>
        <nav className="grid grid-cols-2 gap-x-8 gap-y-3 text-xs font-bold uppercase tracking-wider">{links.map((item) => {
          const href = rewriteLegacyPublicPath(typeof item.href === "string" ? item.href : "/");
          return <Link key={href} href={localizedPath(locale, href)} className="hover:text-lime-300">{resolveLocalizedText(item.label, locale)}</Link>;
        })}</nav>
        <Link href={localizedPath(locale, "/rfq")} className="inline-flex h-fit items-center gap-2 border border-lime-300 px-5 py-3 text-xs font-black uppercase tracking-wider text-lime-300 hover:bg-lime-300 hover:text-black">Send a drawing <ArrowUpRight size={15}/></Link>
      </div>
      <div className="border-t border-white/10 px-6 py-5 text-center text-[10px] uppercase tracking-[0.18em] text-gray-600">ForgeBase test environment · no manufacturing claim · no sales follow-up</div>
    </footer>
  );
}
