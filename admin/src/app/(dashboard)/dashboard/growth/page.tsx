"use client";

import { BarChart2, ListChecks, Mail, SlidersHorizontal, Target, Users } from "lucide-react";

import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const items: WorkspaceItem[] = [
  { title: "內容成效", description: "找出帶來產品探索、下載與詢價行為的內容。", href: "/dashboard/content-performance", icon: BarChart2, feature: "full_tracking", accent: "blue" },
  { title: "等待跟進的買家", description: "依市場、瀏覽內容與近期互動整理需要持續跟進的買家。", href: "/dashboard/segments", icon: Users, feature: "audience_segments", accent: "violet" },
  { title: "動態行動按鈕", description: "依頁面與買家意圖提供下一個合理行動。", href: "/dashboard/ctas", icon: Target, feature: "dynamic_cta", accent: "emerald" },
  { title: "跟進內容與時間", description: "安排第幾天提供哪些資料；流程啟用及寄出前都需要人工確認。", href: "/dashboard/nurture", icon: Mail, feature: "nurture_email", accent: "amber" },
  { title: "寄出前確認", description: "逐封確認收件人、主旨與內容，避免系統未經同意自行寄送。", href: "/dashboard/nurture/outbox", icon: ListChecks, feature: "nurture_email", accent: "amber" },
  { title: "買家關注條件", description: "用可說明的瀏覽、下載與詢價行為整理跟進順序。", href: "/dashboard/intent-rules", icon: SlidersHorizontal, feature: "advanced_intent_rules", accent: "blue" },
];

export default function GrowthWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="潛在買家跟進"
      title="從有興趣到正式詢價"
      description="先找出值得持續聯絡的買家，再安排內容與時間；每一封信都由人員確認後才寄出。"
      items={items}
    />
  );
}
