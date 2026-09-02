"use client";

import { BotMessageSquare, ClipboardList, Eye, MailCheck } from "lucide-react";

import { WorkspaceHub, type FlowStep, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const flow: FlowStep[] = [
  { label: "訪客來源", feature: "full_tracking" },
  { label: "網站瀏覽", feature: "full_tracking" },
  { label: "AI 客服對話", feature: "chat_handoff" },
  { label: "聯絡或詢價" },
  { label: "買家回信", feature: "inbound_reply" },
  { label: "業務接手", feature: "sales_handoff" },
];

const items: WorkspaceItem[] = [
  { title: "訪客旅程", description: "查看來源、瀏覽順序、產品興趣，以及何時形成聯絡或詢價。", href: "/dashboard/visitors", icon: Eye, feature: "full_tracking", accent: "blue" },
  { title: "AI 客服對話", description: "查看網站對話內容；形成詢價後可直接前往對應案件。", href: "/dashboard/chats", icon: BotMessageSquare, feature: "chat_handoff", accent: "amber" },
  { title: "買家回信與接手", description: "查看系統實際收到的回信，交由指定業務接手。", href: "/dashboard/replies", icon: MailCheck, feature: "inbound_reply", accent: "violet" },
  { title: "詢價案件", description: "查看 RFQ 來源、需求內容、負責人及接手狀態。", href: "/dashboard/rfqs", icon: ClipboardList, accent: "emerald" },
];

export default function VisitorSourceWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="訪客與來源"
      title="從訪客來源一路看到業務接手"
      description="這裡只呈現網站與系統能確認的行為，不把電話、視訊、議價或成交假設成網站資料。"
      flow={flow}
      items={items}
    />
  );
}
