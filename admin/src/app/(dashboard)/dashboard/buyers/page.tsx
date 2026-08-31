"use client";

import { ClipboardList, Eye, MailCheck, TrendingUp } from "lucide-react";

import { WorkspaceHub, type FlowStep, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const flow: FlowStep[] = [
  { label: "匿名訪客", feature: "full_tracking" },
  { label: "行為追蹤", feature: "full_tracking" },
  { label: "推測公司", feature: "company_identification" },
  { label: "聯絡窗口", feature: "contact_enrichment" },
  { label: "個人化信件", feature: "journey_personalization" },
  { label: "寄送追蹤", feature: "outreach_send" },
  { label: "買家回覆", feature: "inbound_reply" },
  { label: "真人接手", feature: "sales_handoff" },
  { label: "RFQ／成交" },
];

const items: WorkspaceItem[] = [
  { title: "商機漏斗與成果", description: "檢視從訪客、公司與窗口到回覆、RFQ 和成交的可信轉換漏斗。", href: "/dashboard/outcomes", icon: TrendingUp, feature: "outcomes_dashboard", accent: "emerald" },
  { title: "訪客旅程", description: "查看匿名訪客走過的頁面與事件；不把公司候選誤稱為訪客本人。", href: "/dashboard/visitors", icon: Eye, feature: "full_tracking", accent: "blue" },
  { title: "買家回信與接手", description: "處理外聯回覆、SLA、負責人與 RFQ 轉換，將高價值回覆交給真人業務。", href: "/dashboard/replies", icon: MailCheck, feature: "inbound_reply", accent: "violet" },
  { title: "詢價案件", description: "管理 RFQ 品質、指派、狀態、跟進紀錄與成交結果。", href: "/dashboard/rfqs", icon: ClipboardList, accent: "emerald" },
];

export default function BuyerWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="Buyer Pipeline"
      title="買家管線"
      description="用同一條流程理解匿名訪客、意圖、公司與窗口候選、外聯回覆，以及最後的 RFQ／成交；只呈現有證據的關聯。"
      flow={flow}
      items={items}
    />
  );
}
