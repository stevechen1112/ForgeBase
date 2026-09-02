"use client";

import { ArrowRightLeft, Factory, File, FilePenLine, FolderOpen, GitCompareArrows, HelpCircle, Image, Languages, Package, Trophy, Wrench } from "lucide-react";

import { WorkspaceHub, type WorkspaceItem } from "@/components/workspaces/WorkspaceHub";

const editors = ["owner", "admin", "marketing_manager"] as const;

const items: WorkspaceItem[] = [
  { title: "多語內容", description: "查看各語系覆蓋率，批次產生未發布草稿並逐筆確認後上架。", href: "/dashboard/content/locales", icon: Languages, feature: "multilingual", allowedRoles: [...editors], accent: "emerald" },
  { title: "商品管理", description: "維護商品資料、規格、圖片與公開狀態；業務亦可查閱產品資訊。", href: "/dashboard/products", icon: Package, accent: "blue" },
  { title: "商品分類", description: "整理產品線、分類頁資訊與導覽結構。", href: "/dashboard/categories", icon: FolderOpen, allowedRoles: [...editors], accent: "amber" },
  { title: "頁面管理", description: "維護首頁以外的公司、服務與自訂網站內容。", href: "/dashboard/pages", icon: File, allowedRoles: ["owner", "admin"], accent: "violet" },
  { title: "網站文案與圖片", description: "調整首頁與共用區塊的文字、圖片及品牌表達。", href: "/dashboard/settings/site-copy", icon: FilePenLine, allowedRoles: [...editors], accent: "violet" },
  { title: "圖片與檔案", description: "管理官網圖片、型錄、規格書與替代文字。", href: "/dashboard/assets", icon: Image, allowedRoles: [...editors], accent: "emerald" },
  { title: "應用場景", description: "用採購情境與產業用途組織產品內容。", href: "/dashboard/applications", icon: Factory, allowedRoles: [...editors], accent: "blue" },
  { title: "常見問題", description: "維護 AI 客服與公開網站可使用的問答內容。", href: "/dashboard/faqs", icon: HelpCircle, allowedRoles: [...editors], accent: "amber" },
  { title: "認證管理", description: "集中管理證書、標準與可公開的驗證依據。", href: "/dashboard/certifications", icon: Trophy, allowedRoles: [...editors], accent: "emerald" },
  { title: "廠能介紹", description: "維護製造能力、設備、製程與品質優勢。", href: "/dashboard/capabilities", icon: Wrench, allowedRoles: [...editors], accent: "violet" },
  { title: "產品比較", description: "建立可驗證的產品比較內容，協助買家縮小選擇。", href: "/dashboard/comparisons", icon: GitCompareArrows, feature: "advanced_content", allowedRoles: [...editors], accent: "blue" },
  { title: "SEO 網址轉址", description: "在改版或調整網址時保留既有搜尋流量。", href: "/dashboard/redirects", icon: ArrowRightLeft, feature: "seo_redirects", allowedRoles: ["owner", "admin"], accent: "amber" },
];

export default function ContentWorkspacePage() {
  return (
    <WorkspaceHub
      eyebrow="網站內容"
      title="內容中心"
      description="從一處進入商品、頁面、文件、應用、FAQ、認證與廠能內容。多語草稿與審核會沿用同一份來源內容與治理流程。"
      items={items}
    />
  );
}
