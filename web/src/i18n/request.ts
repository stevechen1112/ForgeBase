import { getRequestConfig } from "next-intl/server";
import { getRuntimeSiteConfig } from "@/lib/runtimeSiteConfig";
import { routing } from "./routing";

type MessageTree = Record<string, unknown>;

function replaceStringTokens(input: string, options: {
  brandName: string;
  contactEmail: string;
  contactPhone: string;
  careersEmail: string;
}): string {
  // Use a placeholder so "NorthForge Tools" → brand, then bare "NorthForge" → brand
  // does not rewrite the brand a second time into "NorthForge Tools Tools".
  const brandToken = "\u0000BRAND\u0000";
  return input
    .replaceAll("NorthForge Tools", brandToken)
    .replaceAll("NorthForge", brandToken)
    .replaceAll("ForgeBase", brandToken)
    .replaceAll(brandToken, options.brandName)
    .replaceAll("hello@forgebase.co", options.contactEmail)
    .replaceAll("sales@northforgetools.com", options.contactEmail)
    .replaceAll("careers@northforgetools.com", options.careersEmail)
    .replaceAll("+886-4-3700-2218", options.contactPhone);
}

function applyTenantTextReplacementsWithConfig(
  value: unknown,
  options: { brandName: string; contactEmail: string; contactPhone: string; careersEmail: string },
): unknown {
  if (typeof value === "string") {
    return replaceStringTokens(value, options);
  }

  if (Array.isArray(value)) {
    return value.map((item) => applyTenantTextReplacementsWithConfig(item, options));
  }

  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [key, applyTenantTextReplacementsWithConfig(item, options)])
    );
  }

  return value;
}

export default getRequestConfig(async ({ requestLocale }) => {
  // requestLocale 是從 middleware/URL 解析出來的語言
  let locale = await requestLocale;

  // 如果不在支援清單內，fallback 到預設語言
  if (!locale || !routing.locales.includes(locale as (typeof routing.locales)[number])) {
    locale = routing.defaultLocale;
  }

  const messages = (await import(`../../messages/${locale}.json`)).default as MessageTree;
  const runtimeSiteConfig = await getRuntimeSiteConfig();

  return {
    locale,
    messages: applyTenantTextReplacementsWithConfig(messages, {
      brandName: runtimeSiteConfig.brandName,
      contactEmail: runtimeSiteConfig.contactEmail,
      contactPhone: runtimeSiteConfig.contactPhone,
      careersEmail: runtimeSiteConfig.careersEmail || runtimeSiteConfig.contactEmail,
    }) as MessageTree,
  };
});
