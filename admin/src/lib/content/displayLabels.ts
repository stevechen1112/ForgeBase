/** Shared zh-TW labels for content page types and buyer intent stages. */

export const PAGE_TYPE_LABELS: Record<string, string> = {
  product: "商品",
  application: "應用場景",
  category: "商品分類",
  comparison: "比較",
  custom: "自訂",
  faq: "常見問題",
  certification: "認證",
  page: "頁面",
  other: "其他",
  resource: "資源下載",
  company: "公司資訊",
  contact: "聯絡我們",
  blog: "文章",
  unknown: "未分類",
};

/** Page types selectable when creating a writing brief. */
export const BRIEF_PAGE_TYPE_OPTIONS = [
  "product",
  "application",
  "category",
  "comparison",
  "faq",
  "certification",
  "custom",
] as const;

export function pageTypeLabel(type: string): string {
  return PAGE_TYPE_LABELS[type] ?? type;
}

export const INTENT_STAGE_LABELS: Record<string, string> = {
  sales_ready: "可成交",
  hot: "高度關注",
  warm: "多次互動",
  cold: "初次瀏覽",
};

export function intentStageLabel(stage: string): string {
  return INTENT_STAGE_LABELS[stage] ?? stage;
}
