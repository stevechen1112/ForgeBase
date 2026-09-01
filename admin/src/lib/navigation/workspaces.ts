import type { LucideIcon } from "lucide-react";
import {
  Bell,
  BookOpenText,
  BotMessageSquare,
  Boxes,
  Building2,
  ChartNoAxesCombined,
  ClipboardCheck,
  ClipboardList,
  FileImage,
  FilePenLine,
  Files,
  FolderTree,
  Gauge,
  GitCompareArrows,
  Globe2,
  Handshake,
  Languages,
  LayoutDashboard,
  LifeBuoy,
  Link2,
  ListChecks,
  MailOpen,
  Megaphone,
  MessageSquareText,
  PackageSearch,
  PanelsTopLeft,
  Route,
  Send,
  Settings2,
  ShieldCheck,
  Target,
  Users,
  UserSearch,
  Wrench,
} from "lucide-react";

import type { UserRead } from "@/lib/api/auth";

export type WorkspaceItem = {
  label: string;
  description: string;
  href: string;
  icon: LucideIcon;
  feature?: string;
  roles?: UserRead["role"][];
  keywords?: string[];
};

export type Workspace = {
  id: string;
  label: string;
  shortLabel: string;
  description: string;
  href: string;
  icon: LucideIcon;
  accent: "cyan" | "blue" | "amber" | "emerald" | "violet" | "rose";
  roles?: UserRead["role"][];
  items: WorkspaceItem[];
};

const editors: UserRead["role"][] = ["owner", "admin", "marketing_manager"];
const admins: UserRead["role"][] = ["owner", "admin"];

/**
 * The single source of truth for tenant-admin navigation.
 *
 * Removed product areas (marketing assistant, buyer scoring, external-service
 * connections and their former routes) must not be added here. A workspace may
 * show a locked capability, but it must never silently disappear.
 */
export const WORKSPACES: Workspace[] = [
  {
    id: "today",
    label: "今日工作",
    shortLabel: "今日工作",
    description: "先看需要立即處理的詢價、待辦與通知。",
    href: "/dashboard/workspaces/today",
    icon: LayoutDashboard,
    accent: "cyan",
    items: [
      { label: "每日營運總覽", description: "掌握今日優先事項與近 30 天營運概況。", href: "/dashboard", icon: Gauge, keywords: ["首頁", "晨報", "KPI"] },
      { label: "今日待辦", description: "集中處理已指派、到期與逾期工作。", href: "/dashboard/tasks", icon: ListChecks, keywords: ["工作", "任務"] },
      { label: "通知中心", description: "查看系統與團隊需要留意的通知。", href: "/dashboard/notifications", icon: Bell },
    ],
  },
  {
    id: "rfq",
    label: "詢價與跟進",
    shortLabel: "詢價與跟進",
    description: "從新詢價、分派、回覆到成交結果都在同一區。",
    href: "/dashboard/workspaces/inquiries",
    icon: ClipboardList,
    accent: "amber",
    items: [
      { label: "全部詢價案件", description: "查看與篩選所有 RFQ 案件。", href: "/dashboard/rfqs", icon: ClipboardList, keywords: ["RFQ", "報價"] },
      { label: "我的詢價案件", description: "只看指派給自己的案件。", href: "/dashboard/rfqs/my", icon: ClipboardCheck },
      { label: "回覆範本", description: "維護業務常用的詢價回覆內容。", href: "/dashboard/rfqs/templates", icon: MessageSquareText },
      { label: "商機漏斗與成果", description: "查看詢價、報價與成交成果。", href: "/dashboard/outcomes", icon: ChartNoAxesCombined, feature: "full_tracking", keywords: ["漏斗", "轉換", "成交"] },
    ],
  },
  {
    id: "buyers",
    label: "買家與客戶",
    shortLabel: "買家與客戶",
    description: "了解買家從瀏覽、對話、回信到詢價的完整脈絡。",
    href: "/dashboard/workspaces/customers",
    icon: Users,
    accent: "blue",
    items: [
      { label: "買家管線", description: "依買家階段查看商機進度。", href: "/dashboard/buyers", icon: Route },
      { label: "訪客旅程", description: "查看匿名訪客的網站互動歷程。", href: "/dashboard/visitors", icon: UserSearch, feature: "full_tracking" },
      { label: "AI 客服對話", description: "查看網站對話並在需要時人工接手。", href: "/dashboard/chats", icon: BotMessageSquare, feature: "chat_handoff" },
      { label: "買家回信與接手", description: "集中處理買家回覆與後續接手。", href: "/dashboard/replies", icon: MailOpen, feature: "inbound_reply" },
    ],
  },
  {
    id: "products",
    label: "產品內容",
    shortLabel: "產品內容",
    description: "維護產品、分類、應用、認證與製造能力。",
    href: "/dashboard/workspaces/product-content",
    icon: Boxes,
    accent: "emerald",
    items: [
      { label: "商品管理", description: "維護產品資料、規格、圖片與公開狀態。", href: "/dashboard/products", icon: PackageSearch },
      { label: "商品分類", description: "整理產品線與前台導覽結構。", href: "/dashboard/categories", icon: FolderTree, roles: editors },
      { label: "應用場景", description: "用產業用途與採購情境組織產品。", href: "/dashboard/applications", icon: Building2, roles: editors },
      { label: "認證管理", description: "管理證書、標準與公開驗證依據。", href: "/dashboard/certifications", icon: ShieldCheck, roles: editors },
      { label: "廠能介紹", description: "維護設備、製程、產能與品質優勢。", href: "/dashboard/capabilities", icon: Wrench, roles: editors },
      { label: "產品比較", description: "建立可驗證的產品比較內容。", href: "/dashboard/comparisons", icon: GitCompareArrows, feature: "advanced_content", roles: editors },
    ],
  },
  {
    id: "website",
    label: "網站內容",
    shortLabel: "網站內容",
    description: "維護頁面、文案、圖片、多語與網站導覽。",
    href: "/dashboard/workspaces/website-content",
    icon: PanelsTopLeft,
    accent: "violet",
    items: [
      { label: "頁面管理", description: "維護公司、服務與自訂頁面。", href: "/dashboard/pages", icon: Files, roles: admins },
      { label: "網站文案與圖片", description: "調整首頁與共用區塊的品牌內容。", href: "/dashboard/settings/site-copy", icon: FilePenLine, roles: editors },
      { label: "圖片與檔案", description: "管理圖片、型錄、規格書與替代文字。", href: "/dashboard/assets", icon: FileImage, roles: editors },
      { label: "多語內容", description: "查看語系覆蓋並逐筆確認草稿。", href: "/dashboard/content/locales", icon: Languages, feature: "multilingual", roles: editors },
      { label: "常見問題", description: "維護網站與客服可使用的問答內容。", href: "/dashboard/faqs", icon: BookOpenText, roles: editors },
      { label: "行動按鈕", description: "維護網站上的詢價與下一步行動。", href: "/dashboard/ctas", icon: Target, feature: "dynamic_cta", roles: editors },
      { label: "SEO 網址轉址", description: "改版時保留既有網址與搜尋流量。", href: "/dashboard/redirects", icon: Link2, feature: "seo_redirects", roles: admins },
    ],
  },
  {
    id: "followup",
    label: "潛在買家跟進",
    shortLabel: "潛在買家跟進",
    description: "從內容成效、買家分群到寄出前人工確認。",
    href: "/dashboard/workspaces/buyer-followup",
    icon: Handshake,
    accent: "rose",
    roles: editors,
    items: [
      { label: "內容成效", description: "找出帶來探索、下載與詢價的內容。", href: "/dashboard/content-performance", icon: ChartNoAxesCombined, feature: "full_tracking" },
      { label: "等待跟進的買家", description: "依市場與近期互動整理跟進名單。", href: "/dashboard/segments", icon: Users, feature: "audience_segments" },
      { label: "跟進內容與時間", description: "安排第幾天提供哪些資料。", href: "/dashboard/nurture", icon: Megaphone, feature: "nurture_email" },
      { label: "寄出前確認", description: "逐封確認收件人、主旨與內容後再寄出。", href: "/dashboard/nurture/outbox", icon: Send, feature: "nurture_email" },
    ],
  },
  {
    id: "team",
    label: "團隊管理",
    shortLabel: "團隊管理",
    description: "管理成員、角色與工作分工。",
    href: "/dashboard/workspaces/team",
    icon: Users,
    accent: "blue",
    roles: admins,
    items: [
      { label: "團隊成員", description: "管理帳號、角色與啟用狀態。", href: "/dashboard/users", icon: Users, roles: admins },
    ],
  },
  {
    id: "settings",
    label: "設定與支援",
    shortLabel: "設定與支援",
    description: "管理公司資料、通知偏好與網站修改需求。",
    href: "/dashboard/workspaces/settings",
    icon: Settings2,
    accent: "cyan",
    items: [
      { label: "公司與網站資料", description: "維護品牌、公司與公開網站基本資料。", href: "/dashboard/settings/site-profile", icon: Globe2, roles: admins },
      { label: "通知設定", description: "調整通知方式與接收範圍。", href: "/dashboard/settings/notifications", icon: Bell },
      { label: "網站修改與支援", description: "提交網站調整需求並查看處理狀態。", href: "/dashboard/support", icon: LifeBuoy },
    ],
  },
];

export const DEFAULT_FAVORITES = [
  "/dashboard",
  "/dashboard/rfqs",
  "/dashboard/products",
  "/dashboard/content/locales",
];

export function isRoleAllowed(
  roles: UserRead["role"][] | undefined,
  role: UserRead["role"] | null,
) {
  return !roles || Boolean(role && roles.includes(role));
}

export function isRouteActive(pathname: string, href: string) {
  if (href === "/dashboard") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function findWorkspace(pathname: string) {
  const workspaceRoute = WORKSPACES.find((workspace) => isRouteActive(pathname, workspace.href));
  if (workspaceRoute) return workspaceRoute;
  const candidates = WORKSPACES.flatMap((workspace) => [
    ...workspace.items.map((item) => ({ workspace, href: item.href })),
  ])
    .filter(({ href }) => isRouteActive(pathname, href))
    .sort((left, right) => right.href.length - left.href.length);
  return candidates[0]?.workspace ?? WORKSPACES[0];
}

export function findCurrentItem(pathname: string) {
  return WORKSPACES.flatMap((workspace) => workspace.items)
    .filter((item) => isRouteActive(pathname, item.href))
    .sort((left, right) => right.href.length - left.href.length)[0];
}
