"use client";

import { BarChart2, Gauge, Mail, Settings2, SlidersHorizontal, Sparkles, Target, Users } from "lucide-react";

import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const items: WorkspaceItem[] = [
  { title: "內容成效", description: "找出帶來產品探索、下載與詢價行為的內容。", href: "/dashboard/content-performance", icon: BarChart2, feature: "full_tracking", accent: "blue" },
  { title: "買家分群", description: "依旅程與行為條件建立可重算的營運受眾。", href: "/dashboard/segments", icon: Users, feature: "audience_segments", accent: "violet" },
  { title: "動態行動按鈕", description: "依頁面與買家意圖提供下一個合理行動。", href: "/dashboard/ctas", icon: Target, feature: "dynamic_cta", accent: "emerald" },
  { title: "培育與跟進郵件", description: "管理已知聯絡人的人工審核序列與寄送佇列。", href: "/dashboard/nurture", icon: Mail, feature: "nurture_email", accent: "amber" },
  { title: "AI 業務助理", description: "查詢營運資料並建立仍需真人核准的跟進動作。", href: "/dashboard/copilot", icon: Sparkles, feature: "ai_copilot", accent: "violet" },
  { title: "進階評分規則", description: "調整各種行為如何影響買家關注分數。", href: "/dashboard/intent-rules", icon: SlidersHorizontal, feature: "advanced_intent_rules", accent: "blue" },
  { title: "預測評分模型", description: "僅在資料與模型 Gate 通過後顯示線上預測能力。", href: "/dashboard/ml-scoring", icon: Gauge, feature: "ml_scoring", allowedRoles: ["owner", "admin"], accent: "amber" },
  { title: "外部服務", description: "檢視由 ForgeBase 管理的郵件、CRM 與其他服務連線。", href: "/dashboard/integrations", icon: Settings2, feature: "integrations", allowedRoles: ["owner", "admin"], accent: "emerald" },
];

export default function GrowthWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="Growth Operations"
      title="成長工具"
      description="這些工具支援北極星流程，但不另外構成第二套產品。頁面只顯示目前成熟且已由營運方啟用的能力。"
      items={items}
    />
  );
}
