/** Stale marketing hrefs that still appear in stored site-profile footers. */
export const LEGACY_PUBLIC_PATHS: Record<string, string> = {
  "/technical-docs": "/docs",
  "/dealer-locator": "/dealers",
  "/cookie-policy": "/cookies",
  "/custom-solutions": "/oem-odm",
};

/** Map a stored public href onto the live route, without a locale prefix. */
export function rewriteLegacyPublicPath(href: string): string {
  if (!href.startsWith("/") || href.startsWith("//")) {
    return href;
  }
  const [pathWithLocale, query] = href.split("?");
  const path = stripLocalePrefix(pathWithLocale);
  const canonical = LEGACY_PUBLIC_PATHS[path] ?? path;
  return query ? `${canonical}?${query}` : canonical;
}
import { stripLocalePrefix } from "@/lib/localizedPath";
