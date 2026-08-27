import { defineRouting } from "next-intl/routing";

export const PUBLIC_LOCALES = ["en", "zh-TW", "ja", "fr", "ru"] as const;
export type Locale = (typeof PUBLIC_LOCALES)[number];

export const LOCALE_NATIVE_NAMES: Record<Locale, string> = {
  en: "English",
  "zh-TW": "繁體中文",
  ja: "日本語",
  fr: "Français",
  ru: "Русский",
};

export const PREFIXED_LOCALES = PUBLIC_LOCALES.filter(
  (locale): locale is Exclude<Locale, "en"> => locale !== "en",
);

export function isPublicLocale(value: string): value is Locale {
  return PUBLIC_LOCALES.includes(value as Locale);
}

export const routing = defineRouting({
  locales: PUBLIC_LOCALES,

  // 預設語言（英文不加前綴，中文顯示 /zh-TW/...）
  defaultLocale: "en",

  // 'as-needed': 預設語言不加前綴，其他語言加前綴
  localePrefix: "as-needed",

  // 生產站首頁固定保留英文根路徑 `/`，避免依瀏覽器語言自動跳轉造成代理錯誤
  localeDetection: false,
});
