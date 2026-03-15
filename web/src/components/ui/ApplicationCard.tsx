import Link from "next/link";
import type { Application } from "@/types/content";

type Props = { application: Application };

export function ApplicationCard({ application }: Props) {
  return (
    <Link
      href={`/applications/${application.slug}`}
      className="group flex flex-col rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md"
    >
      <span className="mb-2 inline-block rounded-full bg-blue-50 px-3 py-0.5 text-xs font-medium text-blue-700">
        {application.industry}
      </span>
      <h3 className="text-base font-semibold text-gray-800 group-hover:text-blue-700 transition-colors line-clamp-2">
        {application.application_name}
      </h3>
      {application.description && (
        <p className="mt-2 text-sm text-gray-500 line-clamp-3">{application.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim()}</p>
      )}
      <span className="mt-4 text-sm font-medium text-blue-700 group-hover:underline">
        Learn more →
      </span>
    </Link>
  );
}
