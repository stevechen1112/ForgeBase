import { defineRouting } from "next-intl/routing";

export const routing = defineRouting({
  // 支援的語言清單
  locales: ["en", "zh-TW"],

  // 預設語言（英文不加前綴，中文顯示 /zh-TW/...）
  defaultLocale: "en",

  // 'as-needed': 預設語言不加前綴，其他語言加前綴
  localePrefix: "as-needed",
});

export type Locale = (typeof routing.locales)[number];
