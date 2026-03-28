"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard, Brain, FileText, BarChart2, Target, Building2,
  Mail, Linkedin, Search, Sparkles, Bot, FlaskConical,
  Scale, FolderOpen, Package, Factory, HelpCircle, Trophy, Wrench,
  MousePointerClick, PenLine, Image, Lock, Link2, Map, File, ClipboardList,
  Inbox, Users, Plug, LogOut, ChevronUp, ChevronRight, Bell, Settings, Filter,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type NavSubItem = {
  label: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
};

type NavItem = {
  label: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
  exact?: boolean;
  badge?: string;
  children?: NavSubItem[];
};

type NavGroup = { title: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    title: "概覽",
    items: [
      { label: "儀表板", href: "/dashboard", icon: LayoutDashboard, exact: true },
    ],
  },
  {
    title: "行銷分析",
    items: [
      {
        label: "意圖分析", href: "/dashboard/intent", icon: Brain,
        children: [
          { label: "ML 意圖評分", href: "/dashboard/ml-scoring", icon: Bot, adminOnly: true },
          { label: "評分規則", href: "/dashboard/intent-rules", icon: Scale },
        ],
      },
      { label: "詢價單追蹤", href: "/dashboard/conversions", icon: FileText },
      { label: "頁面成效分析", href: "/dashboard/content-performance", icon: BarChart2 },
      { label: "行銷漏斗", href: "/dashboard/analytics/funnel", icon: Filter },
      { label: "自訂受眾", href: "/dashboard/segments", icon: Target },
      { label: "企業訪客識別", href: "/dashboard/accounts", icon: Building2 },
    ],
  },
  {
    title: "自動化",
    items: [
      { label: "Nurture 引擎", href: "/dashboard/nurture", icon: Mail },
      { label: "LinkedIn Audience", href: "/dashboard/linkedin", icon: Linkedin },
      { label: "A/B 測試", href: "/dashboard/ab-tests", icon: FlaskConical },
      { label: "整合設定", href: "/dashboard/integrations", icon: Plug },
    ],
  },
  {
    title: "AI / SEO",
    items: [
      { label: "SEO 診斷", href: "/dashboard/seo-audit", icon: Search },
      { label: "AI 內容優化", href: "/dashboard/content-optimizer", icon: Sparkles },
      { label: "Redirect 規則", href: "/dashboard/redirects", icon: Link2 },
    ],
  },
  {
    title: "產品內容",
    items: [
      { label: "商品分類", href: "/dashboard/categories", icon: FolderOpen },
      { label: "商品管理", href: "/dashboard/products", icon: Package },
      { label: "應用場景", href: "/dashboard/applications", icon: Factory },
      { label: "FAQ", href: "/dashboard/faqs", icon: HelpCircle },
      // { label: "競品比較", href: "/dashboard/comparisons", icon: Scale },
      { label: "認證管理", href: "/dashboard/certifications", icon: Trophy },
      { label: "廠能介紹", href: "/dashboard/capabilities", icon: Wrench },
    ],
  },
  {
    title: "內容管理",
    items: [
      // { label: "多語管理", href: "/dashboard/multilingual", icon: Globe },
      { label: "CTA 管理", href: "/dashboard/ctas", icon: MousePointerClick },
      { label: "內容摘要", href: "/dashboard/briefs", icon: PenLine },
      { label: "媒體庫", href: "/dashboard/assets", icon: Image },
      { label: "Download Gate", href: "/dashboard/download-gate", icon: Lock },
      { label: "Entity 關聯", href: "/dashboard/relations", icon: Link2 },
      { label: "策略地圖", href: "/dashboard/strategies", icon: Map },
      { label: "頁面管理", href: "/dashboard/pages", icon: File },
    ],
  },
  {
    title: "詢價管理",
    items: [
      { label: "全部 RFQ", href: "/dashboard/rfqs", icon: ClipboardList, adminOnly: true },
      { label: "我的 RFQ", href: "/dashboard/rfqs/my", icon: Inbox, exact: true },
    ],
  },
  {
    title: "系統",
    items: [
      { label: "使用者管理", href: "/dashboard/users", icon: Users, adminOnly: true },
    ],
  },
];

function getInitials(email: string) {
  return email.split("@")[0].slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const { state, logout } = useAuth();

  const user = state.status === "authenticated" ? state.user : null;
  const isAdmin = user?.role === "admin";
  const [expandedItems, setExpandedItems] = useState<string[]>([]);

  function isActive(item: NavItem) {
    if (item.exact) return pathname === item.href;
    return pathname === item.href || pathname.startsWith(item.href + "/");
  }

  return (
    <TooltipProvider delayDuration={300}>
      <aside className="flex h-screen w-60 flex-col bg-[hsl(var(--sidebar-background))] text-[hsl(var(--sidebar-foreground))]">
        {/* ─── Logo ─── */}
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-white/10 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[hsl(var(--sidebar-primary))] text-xs font-bold text-white shadow-sm">
            NF
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-tight text-white">NorthForge</span>
            <span className="text-[10px] font-medium uppercase tracking-widest text-[hsl(var(--sidebar-foreground))]/40">
              Admin
            </span>
          </div>
        </div>

        {/* ─── Nav ─── */}
        <ScrollArea className="flex-1 px-2 py-3">
          <nav className="space-y-5">
            {NAV_GROUPS.map((group) => {
              const visible = group.items.filter((i) => !i.adminOnly || isAdmin);
              if (!visible.length) return null;
              return (
                <div key={group.title}>
                  <p className="mb-1 px-3 text-[10px] font-semibold uppercase tracking-widest text-[hsl(var(--sidebar-foreground))]/40">
                    {group.title}
                  </p>
                  <ul className="space-y-0.5">
                    {visible.map((item) => {
                      const active = isActive(item);
                      const Icon = item.icon;
                      const hasChildren = !!item.children?.length;
                      const visibleChildren = item.children?.filter(c => !c.adminOnly || isAdmin) ?? [];
                      const anyChildActive = visibleChildren.some(c => pathname === c.href || pathname.startsWith(c.href + "/"));
                      const isExpanded = anyChildActive || expandedItems.includes(item.href);
                      return (
                        <li key={item.href}>
                          <div className={cn("flex items-center", hasChildren && "gap-0.5 pr-1")}>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Link
                                  href={item.href}
                                  className={cn(
                                    "group flex flex-1 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150",
                                    (active || anyChildActive)
                                      ? "bg-[hsl(var(--sidebar-primary))]/15 text-white"
                                      : "text-[hsl(var(--sidebar-foreground))]/70 hover:bg-[hsl(var(--sidebar-accent))] hover:text-white"
                                  )}
                                >
                                  <Icon className={cn("h-4 w-4 shrink-0 transition-colors", (active || anyChildActive) ? "text-[hsl(var(--sidebar-primary))]" : "text-[hsl(var(--sidebar-foreground))]/50 group-hover:text-white")} />
                                  <span className="truncate">{item.label}</span>
                                  {active && !hasChildren && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-[hsl(var(--sidebar-primary))]" />}
                                  {item.badge && (
                                    <Badge variant="secondary" className="ml-auto h-4 px-1.5 text-[10px]">{item.badge}</Badge>
                                  )}
                                </Link>
                              </TooltipTrigger>
                              <TooltipContent side="right" className="text-xs">
                                {item.label}
                              </TooltipContent>
                            </Tooltip>
                            {hasChildren && (
                              <button
                                onClick={() => setExpandedItems(prev =>
                                  prev.includes(item.href) ? prev.filter(h => h !== item.href) : [...prev, item.href]
                                )}
                                className="flex h-7 w-6 shrink-0 items-center justify-center rounded text-[hsl(var(--sidebar-foreground))]/40 hover:text-white transition-colors"
                                aria-label={isExpanded ? "收合" : "展開"}
                              >
                                <ChevronRight className={cn("h-3 w-3 transition-transform duration-200", isExpanded && "rotate-90")} />
                              </button>
                            )}
                          </div>
                          {hasChildren && isExpanded && visibleChildren.length > 0 && (
                            <ul className="mt-0.5 ml-[22px] space-y-0.5 border-l border-white/10 pl-3">
                              {visibleChildren.map(child => {
                                const childActive = pathname === child.href || pathname.startsWith(child.href + "/");
                                const ChildIcon = child.icon;
                                return (
                                  <li key={child.href}>
                                    <Link
                                      href={child.href}
                                      className={cn(
                                        "flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium transition-all duration-150",
                                        childActive
                                          ? "bg-[hsl(var(--sidebar-primary))]/10 text-white"
                                          : "text-[hsl(var(--sidebar-foreground))]/60 hover:bg-[hsl(var(--sidebar-accent))] hover:text-white"
                                      )}
                                    >
                                      <ChildIcon className={cn("h-3.5 w-3.5 shrink-0", childActive ? "text-[hsl(var(--sidebar-primary))]" : "text-[hsl(var(--sidebar-foreground))]/40")} />
                                      <span className="truncate">{child.label}</span>
                                      {childActive && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-[hsl(var(--sidebar-primary))]" />}
                                    </Link>
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                </div>
              );
            })}
          </nav>
        </ScrollArea>

        {/* ─── User zone ─── */}
        {user && (
          <div className="shrink-0 border-t border-white/10 p-3">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-[hsl(var(--sidebar-accent))] focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20">
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-[hsl(var(--sidebar-primary))]/20 text-[hsl(var(--sidebar-primary))] text-xs font-semibold">
                      {getInitials(user.email)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-white leading-none mb-0.5">
                      {user.email.split("@")[0]}
                    </p>
                    <p className="truncate text-[11px] text-[hsl(var(--sidebar-foreground))]/50 leading-none">
                      {isAdmin ? "管理員" : "一般使用者"}
                    </p>
                  </div>
                  <ChevronUp className="h-3.5 w-3.5 shrink-0 text-[hsl(var(--sidebar-foreground))]/40" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="start" className="w-56 mb-1">
                <DropdownMenuLabel className="font-normal">
                  <div className="flex flex-col space-y-1">
                    <p className="text-sm font-medium">{user.email.split("@")[0]}</p>
                    <p className="text-xs text-muted-foreground truncate">{user.email}</p>
                  </div>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem asChild>
                  <Link href="/dashboard/settings" className="flex items-center gap-2 cursor-pointer">
                    <Settings className="h-4 w-4" />
                    帳號設定
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/dashboard" className="flex items-center gap-2 cursor-pointer">
                    <Bell className="h-4 w-4" />
                    通知偏好
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={logout}
                  className="flex items-center gap-2 text-destructive focus:text-destructive cursor-pointer"
                >
                  <LogOut className="h-4 w-4" />
                  登出
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </aside>
    </TooltipProvider>
  );
}
