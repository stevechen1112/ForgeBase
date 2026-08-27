/** Normalize next-intl / UI locale tags to CMS DB locale (zh-TW → zh-tw). */

const ROUTE_TO_CONTENT: Record<string, string> = {
  en: "en",
  "zh-tw": "zh-tw",
  "zh-TW": "zh-tw",
  zh_tw: "zh-tw",
  zh_TW: "zh-tw",
  ja: "ja",
  fr: "fr",
  ru: "ru",
};

export function toContentLocale(raw: string | null | undefined, fallback = "en"): string {
  if (!raw) return fallback;
  if (ROUTE_TO_CONTENT[raw]) return ROUTE_TO_CONTENT[raw];
  const lowered = raw.trim().toLowerCase().replace(/_/g, "-");
  if (lowered === "zh-tw") return "zh-tw";
  if (["en", "ja", "fr", "ru"].includes(lowered)) return lowered;
  return fallback;
}

export function toRouteLocale(raw: string | null | undefined, fallback = "en"): string {
  const contentLocale = toContentLocale(raw, "");
  if (contentLocale === "zh-tw") return "zh-TW";
  return contentLocale || fallback;
}
