"use client";

import { ClipboardList, Eye, MailCheck, TrendingUp } from "lucide-react";

import { WorkspaceHub, type FlowStep, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const flow: FlowStep[] = [
  { label: "網站訪客", feature: "full_tracking" },
  { label: "網站互動", feature: "full_tracking" },
  { label: "公司資料", feature: "company_identification" },
  { label: "聯絡窗口", feature: "contact_enrichment" },
  { label: "跟進內容", feature: "journey_personalization" },
  { label: "人工確認後寄出", feature: "outreach_send" },
  { label: "買家回覆", feature: "inbound_reply" },
  { label: "真人接手", feature: "sales_handoff" },
  { label: "RFQ／成交" },
];

const items: WorkspaceItem[] = [
  { title: "商機漏斗與成果", description: "查看從網站互動到詢價與成交的結果。", href: "/dashboard/outcomes", icon: TrendingUp, feature: "outcomes_dashboard", accent: "emerald" },
  { title: "訪客旅程", description: "查看匿名訪客走過的頁面與事件；不把公司候選誤稱為訪客本人。", href: "/dashboard/visitors", icon: Eye, feature: "full_tracking", accent: "blue" },
  { title: "買家回信與接手", description: "查看買家回信，交由指定業務接手並與詢價案件連結。", href: "/dashboard/replies", icon: MailCheck, feature: "inbound_reply", accent: "violet" },
  { title: "詢價案件", description: "管理 RFQ 品質、指派、狀態、跟進紀錄與成交結果。", href: "/dashboard/rfqs", icon: ClipboardList, accent: "emerald" },
];

export default function BuyerWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="買家與客戶"
      title="買家管線"
      description="依序查看網站互動、可確認的公司與聯絡窗口資料、人工跟進，以及最後的詢價／成交；不把公司候選當成訪客本人。"
      flow={flow}
      items={items}
    />
  );
}
