import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { PREFIXED_LOCALES, routing } from "./i18n/routing";
import { withTenantHost } from "./lib/tenant";

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
      headers: withTenantHost(undefined, request.headers.get("host")),
      next: { revalidate: 60 },
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
