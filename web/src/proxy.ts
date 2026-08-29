import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { PREFIXED_LOCALES, routing } from "./i18n/routing";
import { tenantCacheTag, withServerTenantHost } from "./lib/serverTenant";

const intlMiddleware = createMiddleware(routing);
const PUBLIC_FILE_PATH = /\/[^/]+\.[^/]+$/;

const API_BASE =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function shouldBypassMiddleware(pathname: string) {
  return (
    pathname.startsWith("/_next") ||
    pathname.startsWith("/api") ||
    PUBLIC_FILE_PATH.test(pathname)
  );
}

function isHostname(value: unknown): value is string {
  if (typeof value !== "string" || value.length > 253 || !value.includes(".")) {
    return false;
  }
  return value.split(".").every((label) =>
    /^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(label),
  );
}

async function resolveCanonicalDomain(
  request: NextRequest,
): Promise<NextResponse | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/site-domain-routing`, {
      headers: withServerTenantHost(undefined, request.headers.get("host")),
      cache: "no-store",
    });
    if (!res.ok) return null;
    const data = await res.json();
    if (!data?.redirect_required || !isHostname(data.canonical_hostname)) {
      return null;
    }
    const destination = request.nextUrl.clone();
    destination.protocol = "https:";
    destination.hostname = data.canonical_hostname;
    destination.port = "";
    return NextResponse.redirect(destination, { status: 308 });
  } catch {
    // A routing metadata outage must not take an otherwise healthy site down.
    return null;
  }
}

/**
 * SEO Redirect middleware — resolves 301/302 rules stored in the database
 * before the i18n middleware handles locale routing.
 */
async function resolveRedirect(request: NextRequest): Promise<NextResponse | null> {
  const { pathname } = request.nextUrl;

  if (shouldBypassMiddleware(pathname)) {
    return null;
  }

  try {
    const url = `${API_BASE}/api/v1/content/redirects/resolve?path=${encodeURIComponent(pathname)}`;
    const res = await fetch(url, {
      headers: withServerTenantHost(undefined, request.headers.get("host")),
      next: {
        revalidate: 60,
        tags: [tenantCacheTag(request.headers.get("host"))],
      },
    });
    if (!res.ok) return null;

    const data = await res.json();
    if (!data || !data.to_path) return null;

    const destination = new URL(data.to_path, request.nextUrl.origin);
    const statusCode: number = data.status_code === 302 ? 302 : 301;
    return NextResponse.redirect(destination, { status: statusCode });
  } catch {
    // Network errors must not break the site — fall through silently
    return null;
  }
}

export async function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;

  if (shouldBypassMiddleware(pathname)) {
    return NextResponse.next();
  }

  const canonicalResponse = await resolveCanonicalDomain(request);
  if (canonicalResponse) return canonicalResponse;

  // SEO redirects apply to all paths
  const redirectResponse = await resolveRedirect(request);
  if (redirectResponse) return redirectResponse;

  // Only run next-intl middleware for non-default locale paths.
  // Default locale (English) pages are served directly from non-prefixed
  // routes (e.g. /products → products/page.tsx) without rewriting to
  // /en/products, which avoids the 307 redirect loop caused by the
  // conflict between products/page.tsx and [locale]/products/page.tsx.
  if (PREFIXED_LOCALES.some(
    (locale) => pathname === `/${locale}` || pathname.startsWith(`/${locale}/`),
  )) {
    return intlMiddleware(request);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Run middleware for all page routes; file-like requests bypass locale/redirect handling.
    "/((?!api|_next|_vercel|.*\\..*).*)",
  ],
};
