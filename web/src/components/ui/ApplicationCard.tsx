import { Link } from "@/i18n/navigation";
import type { Application } from "@/types/content";
import { getApplicationImage } from "@/lib/demoAssets";
import { siteConfig as defaultSiteConfig, type SiteConfig } from "@/lib/siteConfig";

type Props = {
  application: Application;
  siteConfig?: SiteConfig;
  locale?: string;
};

export function ApplicationCard({
  application,
  siteConfig = defaultSiteConfig,
  locale = "en",
}: Props) {
  const imageUrl = getApplicationImage(application, siteConfig);
  const isIndustrial = siteConfig.layout === "industrial";
  const learnMoreLabel = locale === "zh-TW" ? "了解更多 →" : "Learn more →";

  return (
    <Link
      href={`/applications/${application.slug}`}
      className={isIndustrial
        ? "group flex flex-col overflow-hidden border border-gray-300 bg-white transition-colors hover:border-primary/50 hover:bg-primary/5"
        : "group flex flex-col rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm transition-shadow hover:shadow-md"}
    >
      {/* Hero image */}
      <div className={isIndustrial ? "relative h-44 w-full overflow-hidden bg-gray-100" : "relative h-44 w-full overflow-hidden bg-slate-100"}>
        {imageUrl ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={application.application_name}
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
        ) : (
          <div className="flex h-full items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
            <svg className="h-12 w-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        <span className={isIndustrial
          ? "absolute bottom-3 left-3 inline-block bg-primary px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-primary-foreground"
          : "absolute bottom-3 left-3 inline-block rounded-full bg-blue-600/90 px-3 py-0.5 text-xs font-medium text-white backdrop-blur-sm"}>
          {application.industry}
        </span>
      </div>

      {/* Text content */}
      <div className="flex flex-col p-5 flex-1">
        <h3 className={isIndustrial
          ? "text-base font-black uppercase tracking-wide text-gray-900 transition-colors group-hover:text-primary line-clamp-2"
          : "text-base font-semibold text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2"}>
          {application.application_name}
        </h3>
        {application.description && (
          <p className="mt-2 text-sm text-gray-500 line-clamp-3">{application.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
        )}
        <span className={isIndustrial
          ? "mt-4 text-xs font-black uppercase tracking-[0.16em] text-primary group-hover:underline"
          : "mt-4 text-sm font-medium text-blue-700 group-hover:underline"}>
          {learnMoreLabel}
        </span>
      </div>
    </Link>
  );
}
