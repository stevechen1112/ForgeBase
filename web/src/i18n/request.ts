import { getRequestConfig } from "next-intl/server";
import { routing } from "./routing";

export default getRequestConfig(async ({ requestLocale }) => {
  // requestLocale 是從 middleware/URL 解析出來的語言
  let locale = await requestLocale;

  // 如果不在支援清單內，fallback 到預設語言
  if (!locale || !routing.locales.includes(locale as "en" | "zh-TW")) {
    locale = routing.defaultLocale;
  }

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
