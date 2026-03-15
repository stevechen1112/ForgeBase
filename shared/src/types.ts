// 頁型列舉 — 對應規格 12.2.9
export type PageType =
  | "homepage"
  | "category"
  | "product"
  | "application"
  | "faq"
  | "comparison"
  | "specification"
  | "certification"
  | "capability"
  | "rfq"
  | "contact"
  | "about";

// 發布狀態
export type PublishStatus = "draft" | "published" | "archived";

// 搜尋意圖類型 — 對應規格 12.2.10
export type SearchIntent =
  | "educational"
  | "comparison"
  | "alternative"
  | "specification"
  | "purchasing";

// 語氣
export type ContentTone = "technical" | "consultative" | "educational";

// AI 內容狀態 — 對應規格 12.4.6
export type AIContentStatus = "ai_generated" | "human_reviewed" | "human_written";

// 使用者角色
export type UserRole = "admin" | "marketing_manager" | "sales";

// Intent Stage — 對應規格 12.6.3
export type IntentStage = "cold" | "warm" | "hot" | "sales_ready";

// 事件名稱 — 對應規格 12.5.1
export type EventName =
  | "page_view"
  | "category_view"
  | "product_view"
  | "application_view"
  | "faq_expand"
  | "comparison_view"
  | "spec_download"
  | "certification_view"
  | "cta_click"
  | "form_start"
  | "form_submit"
  | "rfq_start"
  | "rfq_submit"
  | "return_visit"
  | "session_depth_reached";

// CTA 類型
export type CTAType = "primary" | "secondary";
export type CTAActionType = "link" | "form" | "rfq" | "download" | "scroll";

// RFQ 狀態
export type RFQStatus =
  | "new"
  | "assigned"
  | "in_progress"
  | "quoted"
  | "won"
  | "lost"
  | "expired";

// 替代料號關係類型
export type AlternativePartRelation =
  | "exact_replacement"
  | "compatible"
  | "upgrade";
