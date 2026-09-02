"use client";

import { useParams } from "next/navigation";

import { TodayWorkQueue } from "@/components/workspaces/TodayWorkQueue";
import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";
import { WORKSPACES } from "@/lib/navigation/workspaces";

const HERO_COPY: Record<string, { title: string; description: string; action: string }> = {
  prepare: { title: "先讓網站具備承接詢價的條件", description: "產品、技術底稿、網站頁面與多語內容都在同一個工作區。", action: "開始準備" },
  traffic: { title: "從來源看懂訪客如何形成詢價", description: "查看來源、瀏覽與網站對話；不把匿名訊號當成買家身分。", action: "查看訪客" },
  buyers: { title: "買家資料只服務於詢價交接", description: "保留公司、窗口、來源與需求摘要，不建立 CRM 管線。", action: "查看買家" },
  rfq: { title: "把完整詢價清楚交到負責業務手上", description: "確認資料、分派與接手；後續電話、報價與成交在原有作業處理。", action: "查看詢價" },
  team: { title: "讓每位成員清楚自己的角色與範圍", description: "集中管理團隊帳號、角色與工作權限。", action: "查看團隊" },
  settings: { title: "公司設定與支援集中處理", description: "管理公司資料、通知方式，或提出網站修改需求。", action: "開啟設定" },
};
const STAGE_DETAIL: Record<string, { metrics: [string, string, string][]; caseStudy: { title: string; status: string; facts: [string, string][] }; nextStep: string }> = {
  prepare: { metrics: [["產品與技術底稿","13","產品、規格與證明資料"],["多語待審","2","審核後才公開"],["網站頁面","8","維持可詢價狀態"],["待補圖片","1","不影響既有公開內容"]], caseStudy: { title: "TW-220 Servo Housing", status: "英文已公開・日文待審", facts: [["產品底稿","5,000 pcs 報價規格已齊"],["公開依據","ISO 9001、材質追溯"],["網站承接","產品頁、規格書與詢價按鈕"]] }, nextStep: "完成人工審核後再發布多語頁面；英文產品底稿維持為正式依據。" },
  traffic: { metrics: [["近 30 天訪客","124","16 位重複造訪"],["產品頁瀏覽","386","較上月增加"],["主要市場","德國","以第一方來源判定"],["完成詢價","28","等待業務交接"]], caseStudy: { title: "德國匿名訪客 DE-042", status: "4 次造訪・已下載規格書", facts: [["來源","Google／德國"],["瀏覽內容","Servo Housing 3 次"],["關鍵行為","下載規格書後開啟詢價表單"]] }, nextStep: "等待買家主動留下聯絡資料；系統不猜測匿名訪客身分。" },
  buyers: { metrics: [["可辨識買家","16","來自詢價建立"],["本週新增資料","4","隨詢價建立"],["資料待補","2","聯絡方式不完整"],["網站對話交接","3","已留聯絡資料"]], caseStudy: { title: "Axis Technik GmbH", status: "公司與窗口已確認", facts: [["聯絡窗口","Hannah Weber／採購"],["確認方式","買家提交詢價後建立關聯"],["明確需求","TW-220・5,000 pcs"]] }, nextStep: "連同來源、窗口與需求摘要，建立詢價案件交給負責業務。" },
  rfq: { metrics: [["有效詢價","28","近 30 天"],["新詢價待分派","4","1 筆急件"],["資料待補","3","圖面或交期"],["已完成交接","21","由業務後續處理"]], caseStudy: { title: "DEMO-P2-001・Axis Technik", status: "已完成業務交接", facts: [["需求","TW-220・5,000 pcs・德國"],["資料完整度","圖面、公差、材質與交期已確認"],["交接內容","詢價原文、窗口、來源與附件已備齊"]] }, nextStep: "由業務以適合方式回應買家；系統不要求回填電話、報價或成交狀態。" },
};

export default function WorkspaceLandingPage() {
  const params = useParams<{ workspaceId: string }>();
  const workspace = WORKSPACES.find((item) => item.href.endsWith(`/${params.workspaceId}`));

  if (!workspace) {
    return <div className="rounded-xl border bg-white p-8"><h1>找不到工作區</h1><p className="mt-2 text-slate-600">請從左側選單重新選擇。</p></div>;
  }

  if (workspace.id === "today") {
    return <TodayWorkQueue />;
  }

  const copy = HERO_COPY[workspace.id];
  const detail = STAGE_DETAIL[workspace.id];
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
      title={copy.title}
      description={copy.description}
      items={items}
      primaryAction={{ label: copy.action, href: workspace.items[0].href }}
      sectionTitle={`${workspace.label}的全部功能`}
      metrics={detail?.metrics}
      caseStudy={detail?.caseStudy}
      nextStep={detail?.nextStep}
    />
  );
}
