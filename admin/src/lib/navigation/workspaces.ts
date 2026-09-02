import type { LucideIcon } from "lucide-react";
import { Bell, BookOpenText, BotMessageSquare, Boxes, Building2, ClipboardList, FileImage, FilePenLine, Files, FolderTree, Gauge, GitCompareArrows, Globe2, Languages, LayoutDashboard, LifeBuoy, Link2, ListChecks, MessageSquareText, PackageSearch, Route, SearchCheck, Settings2, ShieldCheck, Target, Users, UserSearch, Wrench } from "lucide-react";
import type { UserRead } from "@/lib/api/auth";

export type WorkspaceItem = { label: string; description: string; href: string; icon: LucideIcon; feature?: string; roles?: UserRead["role"][]; keywords?: string[] };
export type Workspace = { id: string; label: string; shortLabel: string; description: string; href: string; icon: LucideIcon; accent: "cyan" | "blue" | "amber" | "emerald" | "violet" | "rose"; roles?: UserRead["role"][]; items: WorkspaceItem[] };
const editors: UserRead["role"][] = ["owner", "admin", "marketing_manager"];
const admins: UserRead["role"][] = ["owner", "admin"];
const productItems: WorkspaceItem[] = [
  { label: "商品管理", description: "維護產品資料、規格、圖片與公開狀態。", href: "/dashboard/products", icon: PackageSearch },
  { label: "商品分類", description: "整理產品線與前台導覽結構。", href: "/dashboard/categories", icon: FolderTree, roles: editors },
  { label: "應用場景", description: "用產業用途與採購情境組織產品。", href: "/dashboard/applications", icon: Building2, roles: editors },
  { label: "認證管理", description: "管理證書、標準與公開驗證依據。", href: "/dashboard/certifications", icon: ShieldCheck, roles: editors },
  { label: "廠能介紹", description: "維護設備、製程、產能與品質優勢。", href: "/dashboard/capabilities", icon: Wrench, roles: editors },
  { label: "產品比較", description: "建立可驗證的產品比較內容。", href: "/dashboard/comparisons", icon: GitCompareArrows, feature: "advanced_content", roles: editors },
  { label: "頁面管理", description: "維護公司、服務與自訂頁面。", href: "/dashboard/pages", icon: Files, roles: admins },
  { label: "網站文案與圖片", description: "調整首頁與共用區塊的品牌內容。", href: "/dashboard/settings/site-copy", icon: FilePenLine, roles: editors },
  { label: "圖片與檔案", description: "管理圖片、型錄、規格書與替代文字。", href: "/dashboard/assets", icon: FileImage, roles: editors },
  { label: "多語內容", description: "查看語系覆蓋並逐筆確認草稿。", href: "/dashboard/content/locales", icon: Languages, feature: "multilingual", roles: editors },
  { label: "常見問題", description: "維護網站與客服可使用的問答內容。", href: "/dashboard/faqs", icon: BookOpenText, roles: editors },
  { label: "行動按鈕", description: "維護網站上的詢價與下一步行動。", href: "/dashboard/ctas", icon: Target, feature: "dynamic_cta", roles: editors },
  { label: "SEO 網址轉址", description: "改版時保留既有網址與搜尋流量。", href: "/dashboard/redirects", icon: Link2, feature: "seo_redirects", roles: admins },
];
/** ForgeBase ends at verified website-to-sales handoff. CRM follow-up, deal outcomes, nurture campaigns, buyer scoring and external service connections are intentionally absent. */
export const WORKSPACES: Workspace[] = [
  { id:"today", label:"今日工作", shortLabel:"今日工作", description:"先處理今天到期、待分派與待交接的工作。", href:"/dashboard/workspaces/today", icon:LayoutDashboard, accent:"cyan", items:[{label:"每日營運總覽",description:"掌握今天最優先的網站承接與詢價交接工作。",href:"/dashboard",icon:Gauge,keywords:["首頁","晨報","KPI"]},{label:"今日待辦",description:"集中處理已指派、到期與逾期工作。",href:"/dashboard/tasks",icon:ListChecks,keywords:["工作","任務"]},{label:"通知中心",description:"查看系統與團隊需要留意的通知。",href:"/dashboard/notifications",icon:Bell}] },
  { id:"prepare", label:"網站與產品準備", shortLabel:"網站與產品準備", description:"先完成產品、技術底稿與網站內容，讓海外買家看得懂並能詢價。", href:"/dashboard/workspaces/website-product", icon:Boxes, accent:"emerald", items:productItems },
  { id:"traffic", label:"訪客與來源觀察", shortLabel:"訪客與來源觀察", description:"看懂訪客從來源、瀏覽、提問到完成詢價的網站脈絡。", href:"/dashboard/workspaces/visitor-sources", icon:Route, accent:"blue", items:[{label:"訪客旅程",description:"查看匿名訪客的來源、瀏覽與詢價歷程。",href:"/dashboard/visitors",icon:UserSearch,feature:"full_tracking"},{label:"網站對話與人工接手",description:"查看 AI 客服對話；有聯絡資料時交給業務。",href:"/dashboard/chats",icon:BotMessageSquare,feature:"chat_handoff"},{label:"訪客與詢價訊號",description:"用訪客、產品頁、下載與詢價觀察網站承接效果。",href:"/dashboard/buyers",icon:SearchCheck,keywords:["來源","訪客","分析"]}] },
  { id:"buyers", label:"買家與聯絡資料", shortLabel:"買家與聯絡資料", description:"保存詢價所需的公司與聯絡窗口資料，不建立 CRM 管線。", href:"/dashboard/workspaces/buyer-details", icon:Users, accent:"violet", items:[{label:"買家與聯絡人",description:"查看詢價建立的公司、窗口、來源與需求摘要。",href:"/dashboard/buyers",icon:Users}] },
  { id:"rfq", label:"詢價接手與分派", shortLabel:"詢價接手與分派", description:"確認需求、資料與負責人，將完整詢價交給業務處理。", href:"/dashboard/workspaces/inquiries", icon:ClipboardList, accent:"amber", items:[{label:"詢價案件",description:"全體共用同一入口；依權限查看、分派與接手案件。",href:"/dashboard/rfqs",icon:ClipboardList,keywords:["RFQ","詢價","分派","接手"]},{label:"案件分派與交接",description:"確認需求、資料與負責人後，交由業務採適合方式回應。",href:"/dashboard/rfqs",icon:Users},{label:"詢價回覆範本",description:"維護業務常用的詢價確認與補件內容。",href:"/dashboard/rfqs/templates",icon:MessageSquareText}] },
  { id:"team", label:"團隊管理", shortLabel:"團隊管理", description:"管理成員、角色與工作分工。", href:"/dashboard/workspaces/team", icon:Users, accent:"blue", roles:admins, items:[{label:"團隊成員",description:"管理帳號、角色與啟用狀態。",href:"/dashboard/users",icon:Users,roles:admins}] },
  { id:"settings", label:"設定與支援", shortLabel:"設定與支援", description:"管理公司資料、通知偏好與網站修改需求。", href:"/dashboard/workspaces/settings", icon:Settings2, accent:"cyan", items:[{label:"公司與網站資料",description:"維護品牌、公司與公開網站基本資料。",href:"/dashboard/settings/site-profile",icon:Globe2,roles:admins},{label:"通知設定",description:"調整通知方式與接收範圍。",href:"/dashboard/settings/notifications",icon:Bell},{label:"網站修改與支援",description:"提交網站調整需求並查看處理狀態。",href:"/dashboard/support",icon:LifeBuoy}] },
];
export const DEFAULT_FAVORITES = ["/dashboard", "/dashboard/rfqs", "/dashboard/products", "/dashboard/content/locales"];
export function isRoleAllowed(roles: UserRead["role"][] | undefined, role: UserRead["role"] | null) { return !roles || Boolean(role && roles.includes(role)); }
export function isRouteActive(pathname: string, href: string) { return href === "/dashboard" ? pathname === href : pathname === href || pathname.startsWith(`${href}/`); }
export function findWorkspace(pathname: string) { const direct=WORKSPACES.find((w)=>isRouteActive(pathname,w.href)); if(direct)return direct; return WORKSPACES.flatMap((w)=>w.items.map((i)=>({w,href:i.href}))).filter((x)=>isRouteActive(pathname,x.href)).sort((a,b)=>b.href.length-a.href.length)[0]?.w ?? WORKSPACES[0]; }
export function findCurrentItem(pathname: string) { return WORKSPACES.flatMap((w)=>w.items).filter((i)=>isRouteActive(pathname,i.href)).sort((a,b)=>b.href.length-a.href.length)[0]; }
