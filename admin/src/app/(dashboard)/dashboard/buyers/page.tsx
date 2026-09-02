"use client";

import { BotMessageSquare, ClipboardList, Eye, Users } from "lucide-react";

import { WorkspaceHub, type FlowStep, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const flow: FlowStep[] = [
  { label: "訪客來源", feature: "full_tracking" },
  { label: "網站瀏覽", feature: "full_tracking" },
  { label: "AI 客服對話", feature: "chat_handoff" },
  { label: "留下聯絡資料或詢價" },
  { label: "建立買家資料" },
  { label: "詢價交給業務", feature: "sales_handoff" },
];

const items: WorkspaceItem[] = [
  { title: "訪客旅程", description: "查看來源、瀏覽順序、產品興趣，以及何時形成聯絡或詢價。", href: "/dashboard/visitors", icon: Eye, feature: "full_tracking", accent: "blue" },
  { title: "AI 客服對話", description: "查看網站對話內容；形成詢價後可直接前往對應案件。", href: "/dashboard/chats", icon: BotMessageSquare, feature: "chat_handoff", accent: "amber" },
  { title: "買家與聯絡人", description: "查看由詢價建立的公司、窗口、來源與需求摘要。", href: "/dashboard/buyers", icon: Users, accent: "violet" },
  { title: "詢價案件", description: "查看 RFQ 來源、需求內容、負責人及接手狀態。", href: "/dashboard/rfqs", icon: ClipboardList, accent: "emerald" },
];

export default function VisitorSourceWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="買家與聯絡資料"
      title="從網站訊號確認買家資料，再交給業務接手"
      description="這裡只保留網站可確認的公司與窗口資料；電話、視訊、議價與成交不屬於本系統的追蹤範圍。"
      flow={flow}
      items={items}
    />
  );
}
