"use client";

import Link from "next/link";
import { ArrowLeft, ChevronRight, Home } from "lucide-react";

import { Button } from "@/components/ui/button";

export type NavigationCrumb = {
  href: string;
  label: string;
};

type RouteGroup = {
  base: string;
  label: string;
  parentHref: string;
  parentLabel: string;
  entityLabel?: string;
  childLabels?: Record<string, string>;
};

const DASHBOARD_HUBS: Record<string, string> = {
  "/dashboard/buyers": "買家管線",
  "/dashboard/content": "內容中心",
  "/dashboard/growth": "潛在買家跟進",
};

const DASHBOARD_GROUPS: RouteGroup[] = [
  { base: "/dashboard/content/locales", label: "多語內容", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/settings/site-copy", label: "網站文案與圖片", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/products", label: "商品管理", entityLabel: "商品", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/categories", label: "商品分類", entityLabel: "分類", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/pages", label: "頁面管理", entityLabel: "頁面", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/assets", label: "圖片與檔案", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/applications", label: "應用場景", entityLabel: "應用場景", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/faqs", label: "常見問題", entityLabel: "常見問題", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/certifications", label: "認證管理", entityLabel: "認證", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/capabilities", label: "廠能介紹", entityLabel: "廠能", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/comparisons", label: "產品比較", entityLabel: "產品比較", parentHref: "/dashboard/workspaces/product-content", parentLabel: "產品內容" },
  { base: "/dashboard/redirects", label: "SEO 網址轉址", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },

  { base: "/dashboard/outcomes", label: "商機漏斗與成果", parentHref: "/dashboard/workspaces/inquiries", parentLabel: "詢價與跟進" },
  { base: "/dashboard/visitors", label: "訪客旅程", entityLabel: "訪客旅程", parentHref: "/dashboard/buyers", parentLabel: "買家管線" },
  { base: "/dashboard/replies", label: "買家回信與接手", parentHref: "/dashboard/buyers", parentLabel: "買家管線" },
  { base: "/dashboard/rfqs", label: "詢價案件", entityLabel: "詢價案件", parentHref: "/dashboard/workspaces/inquiries", parentLabel: "詢價與跟進", childLabels: { my: "我的詢價案件", templates: "回覆範本" } },

  { base: "/dashboard/content-performance", label: "內容成效", parentHref: "/dashboard/workspaces/buyer-followup", parentLabel: "潛在買家跟進" },
  { base: "/dashboard/segments", label: "等待跟進的買家", entityLabel: "買家條件", parentHref: "/dashboard/workspaces/buyer-followup", parentLabel: "潛在買家跟進" },
  { base: "/dashboard/ctas", label: "行動按鈕", entityLabel: "行動按鈕", parentHref: "/dashboard/workspaces/website-content", parentLabel: "網站內容" },
  { base: "/dashboard/nurture", label: "跟進內容與時間", entityLabel: "跟進流程", parentHref: "/dashboard/workspaces/buyer-followup", parentLabel: "潛在買家跟進", childLabels: { outbox: "寄出前確認" } },

  { base: "/dashboard/chats", label: "AI 客服對話", entityLabel: "客服對話", parentHref: "/dashboard/workspaces/customers", parentLabel: "買家與客戶" },
  { base: "/dashboard/tasks", label: "今日待辦", parentHref: "/dashboard/workspaces/today", parentLabel: "今日工作" },
  { base: "/dashboard/notifications", label: "通知中心", parentHref: "/dashboard/workspaces/today", parentLabel: "今日工作" },
  { base: "/dashboard/users", label: "團隊成員", parentHref: "/dashboard/workspaces/team", parentLabel: "團隊管理" },
  { base: "/dashboard/settings/site-profile", label: "公司與網站資料", parentHref: "/dashboard/workspaces/settings", parentLabel: "設定與支援" },
  { base: "/dashboard/settings/notifications", label: "通知設定", parentHref: "/dashboard/workspaces/settings", parentLabel: "設定與支援" },
  { base: "/dashboard/support", label: "網站修改與支援", parentHref: "/dashboard/workspaces/settings", parentLabel: "設定與支援" },
];

const PLATFORM_LABELS: Record<string, string> = {
  overview: "平台總覽",
  tenants: "租戶管理",
  users: "使用者管理",
  applications: "導入申請",
  templates: "網站範本",
  workspace: "網站交付工作台",
  rfqs: "全站詢價",
  "company-identification": "公司推測",
  "contact-enrichment": "聯絡窗口補全",
  outreach: "外聯審核",
  delivery: "寄送與回覆",
  privacy: "隱私治理",
  retirement: "退場治理",
  resources: "平台資源",
  usage: "用量與成本",
  health: "平台健康",
  audit: "稽核紀錄",
};

function detailLabel(group: RouteGroup, remainder: string): string | null {
  if (!remainder) return null;
  const parts = remainder.replace(/^\//, "").split("/").filter(Boolean);
  if (parts.length === 1 && group.childLabels?.[parts[0]]) return group.childLabels[parts[0]];
  if (parts[0] === "new") return `新增${group.entityLabel ?? group.label}`;
  if (parts.at(-1) === "edit") return `編輯${group.entityLabel ?? group.label}`;
  return `${group.entityLabel ?? group.label}詳情`;
}

export function resolveDashboardTrail(pathname: string): NavigationCrumb[] {
  if (pathname === "/dashboard") return [];
  if (pathname.startsWith("/dashboard/workspaces/")) return [];
  const hubLabel = DASHBOARD_HUBS[pathname];
  if (hubLabel) {
    return [
      { href: "/dashboard", label: "每日營運總覽" },
      { href: pathname, label: hubLabel },
    ];
  }

  const group = DASHBOARD_GROUPS
    .filter((candidate) => pathname === candidate.base || pathname.startsWith(`${candidate.base}/`))
    .sort((left, right) => right.base.length - left.base.length)[0];
  if (!group) {
    return [
      { href: "/dashboard", label: "每日營運總覽" },
      { href: pathname, label: "目前頁面" },
    ];
  }

  const trail: NavigationCrumb[] = [{ href: "/dashboard", label: "每日營運總覽" }];
  if (group.parentHref !== "/dashboard") {
    trail.push({ href: group.parentHref, label: group.parentLabel });
  }
  trail.push({ href: group.base, label: group.label });
  const currentDetailLabel = detailLabel(group, pathname.slice(group.base.length));
  if (currentDetailLabel) trail.push({ href: pathname, label: currentDetailLabel });
  return trail;
}

export function resolvePlatformTrail(pathname: string): NavigationCrumb[] {
  if (pathname === "/platform" || pathname === "/platform/overview") return [];
  const parts = pathname.replace(/^\/platform\/?/, "").split("/").filter(Boolean);
  const section = parts[0];
  if (!section) return [];
  const sectionHref = `/platform/${section}`;
  const sectionLabel = PLATFORM_LABELS[section] ?? "平台功能";
  const trail: NavigationCrumb[] = [{ href: "/platform/overview", label: "平台總覽" }];
  trail.push({ href: sectionHref, label: sectionLabel });
  if (parts.length > 1) {
    trail.push({ href: pathname, label: parts[1] === "new" ? `新增${sectionLabel}` : `${sectionLabel}詳情` });
  }
  return trail;
}

export function ContextNavigation({ trail }: { trail: NavigationCrumb[] }) {
  if (trail.length < 2) return null;
  const parent = trail[trail.length - 2];

  return (
    <div className="sticky top-0 z-20 -mx-4 mb-5 border-b bg-background/95 px-4 py-2.5 backdrop-blur supports-[backdrop-filter]:bg-background/85 sm:-mx-6 sm:px-6">
      <div className="flex min-w-0 items-center gap-2">
        <Button asChild variant="ghost" size="sm" className="h-8 shrink-0 px-2 text-muted-foreground hover:text-foreground">
          <Link href={parent.href} aria-label={`返回${parent.label}`}>
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">返回{parent.label}</span>
            <span className="sm:hidden">返回</span>
          </Link>
        </Button>
        <div className="h-5 w-px shrink-0 bg-border" aria-hidden="true" />
        <nav aria-label="頁面階層" className="min-w-0 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <ol className="flex min-w-max items-center gap-1 text-xs text-muted-foreground">
            {trail.map((crumb, index) => {
              const current = index === trail.length - 1;
              return (
                <li key={`${crumb.href}-${index}`} className="flex items-center gap-1">
                  {index > 0 && <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" aria-hidden="true" />}
                  {current ? (
                    <span className="max-w-48 truncate font-medium text-foreground" aria-current="page">{crumb.label}</span>
                  ) : (
                    <Link href={crumb.href} className="inline-flex items-center gap-1 rounded-sm hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary">
                      {index === 0 && <Home className="h-3.5 w-3.5" aria-hidden="true" />}
                      <span>{crumb.label}</span>
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </nav>
      </div>
    </div>
  );
}
