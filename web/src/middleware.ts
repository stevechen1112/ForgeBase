import createMiddleware from "next-intl/middleware";
import { type NextRequest, NextResponse } from "next/server";
import { routing } from "./i18n/routing";

const intlMiddleware = createMiddleware(routing);
const PUBLIC_FILE_PATH = /\/[^/]+\.[^/]+$/;

const API_BASE =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

function shouldBypassMiddleware(pathname: string) {
  return pathname.startsWith("/_next") || pathname.startsWith("/api") || PUBLIC_FILE_PATH.test(pathname);
}

/**
 * SEO Redirect middleware — resolves 301/302 rules stored in the database
 * before the i18n middleware handles locale routing.
 *
 * Only runs for paths that are NOT Next.js internals or API proxy calls.
 */
async function resolveRedirect(request: NextRequest): Promise<NextResponse | null> {
  const { pathname } = request.nextUrl;

  // Skip Next.js internals, API proxy, and static files
  if (shouldBypassMiddleware(pathname)) {
    return null;
  }

  try {
    const url = `${API_BASE}/api/v1/content/redirects/resolve?path=${encodeURIComponent(pathname)}`;
    const res = await fetch(url, {
      next: { revalidate: 60 }, // cache resolve results for 60 s
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

export default async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === "/") {
    const redirectResponse = await resolveRedirect(request);
    if (redirectResponse) return redirectResponse;

    return NextResponse.next();
  }

  if (shouldBypassMiddleware(request.nextUrl.pathname)) {
    return NextResponse.next();
  }

  const redirectResponse = await resolveRedirect(request);
  if (redirectResponse) return redirectResponse;

  return intlMiddleware(request);
}

export const config = {
  matcher: [
    // Run middleware for page routes only; file-like requests must bypass locale/redirect handling.
    "/((?!api|_next|_vercel|.*\\..*).*)",
  ],
};
