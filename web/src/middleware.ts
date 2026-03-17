import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // 符合所有路由，但排除 API、靜態檔案、Next.js 內部路由
  matcher: [
    // 首頁和所有帶語言前綴的路由
    "/",
    "/(zh-TW)/:path*",
    // 排除 preview、_next、api、robots、sitemap、favicon
    "/((?!_next|api|preview|robots|sitemap|favicon|demo|.*\\.).*)",
  ],
};
