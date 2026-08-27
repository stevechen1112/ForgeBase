import { PUBLIC_LOCALES } from "@/i18n/routing";
import { toRouteLocale } from "@/lib/contentLocale";

export function stripLocalePrefix(path: string): string {
  for (const candidate of PUBLIC_LOCALES) {
    if (path === `/${candidate}`) return "/";
    if (path.toLowerCase().startsWith(`/${candidate.toLowerCase()}/`)) {
      return path.slice(candidate.length + 1) || "/";
    }
  }
  return path;
}

export function localizedPath(locale: string, path: string): string {
  if (!path.startsWith("/") || path.startsWith("//")) return path;
  const routeLocale = toRouteLocale(locale);
  const [pathAndQuery, hash = ""] = path.split("#", 2);
  const [pathname, query = ""] = pathAndQuery.split("?", 2);
  const unprefixed = stripLocalePrefix(pathname) || "/";
  const localized = routeLocale === "en"
    ? unprefixed
    : unprefixed === "/" ? `/${routeLocale}` : `/${routeLocale}${unprefixed}`;
  return `${localized}${query ? `?${query}` : ""}${hash ? `#${hash}` : ""}`;
}
