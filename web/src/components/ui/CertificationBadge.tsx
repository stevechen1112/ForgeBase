"use client";

import Link from "next/link";
import type { Certification } from "@/types/content";
import { trackSpecDownload } from "@/lib/analytics";
import { withBasePath } from "@/lib/basePath";
import { siteConfig } from "@/lib/siteConfig";

type Props = { certification: Certification; locale?: string };

const CERT_BADGE_VERSION = "20260318a";

function resolveLocale(locale: string) {
  return locale === "zh-TW" ? "zh-TW" : "en";
}

function buildDetailHref(locale: string, slug: string) {
  const localeKey = resolveLocale(locale);
  // localePrefix is "as-needed": English has no /en prefix
  const prefix = localeKey === "zh-TW" ? "/zh-TW" : "";
  return `${prefix}/certifications/${slug}`;
}

export function CertificationBadge({ certification, locale }: Props) {
  const localeKey = resolveLocale(locale ?? certification.locale);
  const isTestScenario = process.env.NEXT_PUBLIC_BASE_PATH === "/northforge-tools";
  const detailHref = buildDetailHref(localeKey, certification.slug);
  const isIndustrial = siteConfig.layout === "industrial";
  const badgeImageSrc = certification.badge_image_url
    ? `${withBasePath(certification.badge_image_url)}?v=${CERT_BADGE_VERSION}`
    : null;
  const validUntilLabel = localeKey === "zh-TW" ? "有效至" : "Valid until";
  const expiredLabel = localeKey === "zh-TW" ? "已過期" : "Expired";
  const downloadLabel = localeKey === "zh-TW" ? "下載證書" : "Download Certificate";
  const isExpired = certification.expires_at
    ? new Date(certification.expires_at).getTime() < Date.now()
    : false;

  return (
    <div className={isIndustrial
      ? "flex flex-col items-center border border-gray-300 bg-white p-5 text-center"
      : "flex flex-col items-center rounded-xl border border-gray-100 bg-white p-5 shadow-sm text-center"}>
      <Link href={detailHref} className="flex flex-col items-center">
        {badgeImageSrc ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={badgeImageSrc}
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
        <p className={isIndustrial
          ? "text-sm font-black uppercase tracking-wide text-gray-900 transition-colors hover:text-primary"
          : "text-sm font-semibold text-gray-800 hover:text-blue-700 transition-colors"}>{certification.cert_name}</p>
      </Link>
      {certification.issuer && (
        <p className="mt-0.5 text-xs text-gray-500">{certification.issuer}</p>
      )}
      {isTestScenario && (
        <p className="mt-2 border border-amber-300 bg-amber-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-amber-900">
          {localeKey === "zh-TW" ? "測試情境・非真實認證" : "Test scenario · not a real certification"}
        </p>
      )}
      {certification.expires_at && (
        <p className={`mt-1 text-xs ${isExpired ? "font-semibold text-red-600" : "text-gray-400"}`}>
          {isExpired ? expiredLabel : `${validUntilLabel} ${new Date(certification.expires_at).getFullYear()}`}
        </p>
      )}
      {certification.document_url && (
        <a
          href={withBasePath(certification.document_url)}
          target="_blank"
          rel="noopener noreferrer"
          className={isIndustrial
            ? "mt-3 text-[11px] font-black uppercase tracking-[0.16em] text-primary hover:underline"
            : "mt-3 text-xs font-medium text-blue-600 hover:underline"}
          onClick={() => trackSpecDownload(certification.id, certification.cert_name)}
        >
          {downloadLabel}
        </a>
      )}
    </div>
  );
}
