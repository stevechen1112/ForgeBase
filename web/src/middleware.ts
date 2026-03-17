import createMiddleware from "next-intl/middleware";
import { routing } from "./i18n/routing";

export default createMiddleware(routing);

export const config = {
  // 只攔截非預設語言前綴，英文無前綴路由改由實體頁面處理
  matcher: [
    "/(zh-TW)/:path*",
  ],
};
