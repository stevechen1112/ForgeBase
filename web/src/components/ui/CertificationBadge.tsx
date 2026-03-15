"use client";

import Link from "next/link";
import type { Certification } from "@/types/content";
import { trackSpecDownload } from "@/lib/analytics";

type Props = { certification: Certification };

export function CertificationBadge({ certification }: Props) {
  const detailHref = `/certifications/${certification.slug}`;

  return (
    <div className="flex flex-col items-center rounded-xl border border-gray-100 bg-white p-5 shadow-sm text-center">
      <Link href={detailHref} className="flex flex-col items-center">
        {certification.badge_image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={certification.badge_image_url}
            alt={certification.cert_name}
            className="mb-3 h-16 w-16 object-contain"
          />
        ) : (
          <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-amber-50">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-8 w-8 text-amber-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"
              />
            </svg>
          </div>
        )}
        <p className="text-sm font-semibold text-gray-800 hover:text-blue-700 transition-colors">{certification.cert_name}</p>
      </Link>
      {certification.issuer && (
        <p className="mt-0.5 text-xs text-gray-500">{certification.issuer}</p>
      )}
      {certification.expires_at && (
        <p className="mt-1 text-xs text-gray-400">
          Valid until {new Date(certification.expires_at).getFullYear()}
        </p>
      )}
      {certification.document_url && (
        <a
          href={certification.document_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 text-xs font-medium text-blue-600 hover:underline"
          onClick={() => trackSpecDownload(certification.id, certification.cert_name)}
        >
          Download Certificate
        </a>
      )}
    </div>
  );
}
