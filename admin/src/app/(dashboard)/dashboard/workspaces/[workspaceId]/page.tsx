"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { WORKSPACES } from "@/lib/navigation/workspaces";

const HERO_COPY: Record<string, { title: string; description: string; action: string }> = {
  today: { title: "今天必須完成的工作", description: "先處理今天到期、逾期與需要決定的工作。", action: "開始處理" },
  prepare: { title: "先讓網站具備承接詢價的條件", description: "產品、技術底稿、網站頁面與多語內容都在同一個工作區。", action: "開始準備" },
  traffic: { title: "從來源看懂訪客如何形成詢價", description: "查看來源、瀏覽與網站對話；不把匿名訊號當成買家身分。", action: "查看訪客" },
  buyers: { title: "買家資料只服務於詢價交接", description: "保留公司、窗口、來源與需求摘要，不建立 CRM 管線。", action: "查看買家" },
  rfq: { title: "把完整詢價清楚交到負責業務手上", description: "確認資料、分派與接手；後續電話、報價與成交在原有作業處理。", action: "查看詢價" },
  team: { title: "讓每位成員清楚自己的角色與範圍", description: "集中管理團隊帳號、角色與工作權限。", action: "查看團隊" },
  settings: { title: "公司設定與支援集中處理", description: "管理公司資料、通知方式，或提出網站修改需求。", action: "開啟設定" },
};

type TaskQueue = { total_open: number };

export default function WorkspaceLandingPage() {
  const params = useParams<{ workspaceId: string }>();
  const { state } = useAuth();
  const [todayCount, setTodayCount] = useState<number | null>(null);
  const workspace = WORKSPACES.find((item) => item.href.endsWith(`/${params.workspaceId}`));
  const token = state.status === "authenticated" ? state.accessToken : "";

  useEffect(() => {
    if (!token || workspace?.id !== "today") return;
    apiClient.get<TaskQueue>("/ops/task-queue", token)
      .then((queue) => setTodayCount(queue.total_open))
      .catch(() => setTodayCount(null));
  }, [token, workspace?.id]);

  if (!workspace) {
    return <div className="rounded-xl border bg-white p-8"><h1>找不到工作區</h1><p className="mt-2 text-slate-600">請從左側選單重新選擇。</p></div>;
  }

  const copy = HERO_COPY[workspace.id];
  const title = workspace.id === "today" && todayCount !== null ? `今天必須完成 ${todayCount} 項` : copy.title;
  const items: WorkspaceItem[] = workspace.items.map((item, index) => ({
    title: item.label,
    description: item.description,
    href: item.href,
    icon: item.icon,
    feature: item.feature,
    allowedRoles: item.roles,
    accent: (["blue", "emerald", "amber", "violet"] as const)[index % 4],
  }));

  return (
    <WorkspaceHub
      eyebrow={workspace.label}
      title={title}
      description={copy.description}
      items={items}
      primaryAction={{ label: copy.action, href: workspace.items[0].href }}
      sectionTitle={`${workspace.label}的全部功能`}
    />
  );
}
