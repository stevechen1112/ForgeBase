import Link from "next/link";
import type { Application } from "@/types/content";
import { getApplicationImage } from "@/lib/demoAssets";

type Props = { application: Application };

export function ApplicationCard({ application }: Props) {
  const imageUrl = getApplicationImage(application.slug, application.hero_image_url);

  return (
    <Link
      href={`/applications/${application.slug}`}
      className="group flex flex-col rounded-xl border border-gray-200 bg-white overflow-hidden shadow-sm transition-shadow hover:shadow-md"
    >
      {/* Hero image */}
      <div className="relative h-44 w-full overflow-hidden bg-slate-100">
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
        <span className="absolute bottom-3 left-3 inline-block rounded-full bg-blue-600/90 px-3 py-0.5 text-xs font-medium text-white backdrop-blur-sm">
          {application.industry}
        </span>
      </div>

      {/* Text content */}
      <div className="flex flex-col p-5 flex-1">
        <h3 className="text-base font-semibold text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2">
          {application.application_name}
        </h3>
        {application.description && (
          <p className="mt-2 text-sm text-gray-500 line-clamp-3">{application.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
        )}
        <span className="mt-4 text-sm font-medium text-blue-700 group-hover:underline">
          Learn more →
        </span>
      </div>
    </Link>
  );
}
