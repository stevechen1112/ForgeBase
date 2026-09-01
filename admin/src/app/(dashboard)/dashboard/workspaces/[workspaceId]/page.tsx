"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { WORKSPACES } from "@/lib/navigation/workspaces";

const HERO_COPY: Record<string, { title: string; description: string; action: string }> = {
  today: { title: "今天必須完成的工作", description: "先處理今天到期、逾期與需要決定的工作。", action: "開始處理" },
  rfq: { title: "從收到詢價一路跟進到成交", description: "詢價、分派、回覆與成交結果都從這裡進入。", action: "查看詢價" },
  buyers: { title: "先看最值得業務接手的買家", description: "保留訪客、對話、回信與詢價之間的完整脈絡。", action: "查看買家" },
  products: { title: "產品資料集中維護，避免版本不一致", description: "產品、分類、規格、認證與製造能力都在這裡。", action: "查看產品" },
  website: { title: "網站內容都在同一個工作區", description: "頁面、圖片、多語、FAQ 與網址導覽不必分散尋找。", action: "查看內容" },
  followup: { title: "從有興趣到正式詢價", description: "先整理待跟進買家，再安排內容與時間；寄出前由人員確認。", action: "開始跟進" },
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
