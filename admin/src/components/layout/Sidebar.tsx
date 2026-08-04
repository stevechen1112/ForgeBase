"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, Brain, FileText, BarChart2, Target,
  Sparkles, Bot,
  Scale, FolderOpen, Package, Factory, HelpCircle, Trophy, Wrench,
  MousePointerClick, PenLine, Image, Link2, Map, File, ClipboardList,
  Inbox, Users, Plug, LogOut, ChevronUp, ChevronRight, Bell, Settings, Globe, MessageSquare,
  Lock, ListOrdered, TrendingUp, ListChecks, Languages, Mail,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { usePlan } from "@/lib/hooks/usePlan";
import { agentosApi } from "@/lib/api/agentos";
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
  /** Hidden from sales role (visible to marketing_manager, owner, admin). */
  salesHidden?: boolean;
  /** Feature key from PLAN_MATRIX. Item is locked for plans without this feature. */
  requiredFeature?: string;
};

type NavItem = {
  label: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
  /** Hidden from sales role (visible to marketing_manager, owner, admin). */
  salesHidden?: boolean;
  exact?: boolean;
  badge?: string;
  children?: NavSubItem[];
  /** Feature key from PLAN_MATRIX. Item is locked for plans without this feature. */
  requiredFeature?: string;
};

type NavGroup = { title: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    title: "每日營運",
    items: [
      { label: "每日營運總覽", href: "/dashboard", icon: LayoutDashboard, exact: true },
      { label: "今日必處理", href: "/dashboard/tasks", icon: ListChecks },
      { label: "成果總覽", href: "/dashboard/outcomes", icon: TrendingUp },
      { label: "我的 RFQ", href: "/dashboard/rfqs/my", icon: Inbox, exact: true },
      // 全部 RFQ = 全局看板；Sales 與行銷經理都需要看到
      { label: "全部 RFQ", href: "/dashboard/rfqs", icon: ClipboardList, exact: true },
      { label: "回覆範本", href: "/dashboard/rfqs/templates", icon: FileText },
      { label: "通知中心", href: "/dashboard/notifications", icon: Bell },
    ],
  },
  {
    title: "成長分析",
    items: [
      {
        label: "意圖分析", href: "/dashboard/intent", icon: Brain,
        requiredFeature: "intent_scoring",
        children: [
          { label: "ML 意圖評分", href: "/dashboard/ml-scoring", icon: Bot, adminOnly: true, requiredFeature: "intent_scoring" },
          // 評分規則屬內容操作層，Sales 不需要設定
          { label: "評分規則", href: "/dashboard/intent-rules", icon: Scale, requiredFeature: "intent_scoring", salesHidden: true },
        ],
      },
      { label: "頁面成效分析", href: "/dashboard/content-performance", icon: BarChart2, requiredFeature: "full_tracking", salesHidden: true },
      { label: "對話管理", href: "/dashboard/chats", icon: MessageSquare, requiredFeature: "chat_handoff" },
      // Sales 不需要 Copilot 操作介面；他們透過通知接收結果
      { label: "AI 行銷專員", href: "/dashboard/copilot", icon: Bot, salesHidden: true },
      { label: "Agent 任務佇列", href: "/dashboard/agent-runs", icon: ListOrdered, salesHidden: true },
      { label: "自訂受眾", href: "/dashboard/segments", icon: Target, requiredFeature: "full_tracking", salesHidden: true },
      { label: "潛客培育信", href: "/dashboard/nurture", icon: Mail, requiredFeature: "nurture_email", salesHidden: true,
        children: [
          { label: "待寄佇列", href: "/dashboard/nurture/outbox", icon: Inbox, requiredFeature: "nurture_email", salesHidden: true },
        ],
      },
    ],
  },
  {
    title: "內容與網站基建",
    items: [
      // Sales 需要查閱商品規格以回覆客戶，但不需要管理分類與內容
      { label: "商品管理", href: "/dashboard/products", icon: Package },
      { label: "商品分類", href: "/dashboard/categories", icon: FolderOpen, salesHidden: true },
      { label: "AI 內容優化", href: "/dashboard/content-optimizer", icon: Sparkles, requiredFeature: "ai_content_generation", salesHidden: true },
      { label: "多語覆蓋率", href: "/dashboard/multilingual", icon: Languages, requiredFeature: "multilingual", salesHidden: true },
      { label: "策略地圖", href: "/dashboard/strategies", icon: Map, salesHidden: true },
      { label: "內容摘要", href: "/dashboard/briefs", icon: PenLine, salesHidden: true },
      { label: "頁面管理", href: "/dashboard/pages", icon: File, salesHidden: true },
      { label: "媒體庫", href: "/dashboard/assets", icon: Image, salesHidden: true },
      { label: "應用場景", href: "/dashboard/applications", icon: Factory, salesHidden: true },
      { label: "FAQ", href: "/dashboard/faqs", icon: HelpCircle, salesHidden: true },
      { label: "認證管理", href: "/dashboard/certifications", icon: Trophy, salesHidden: true },
      { label: "廠能介紹", href: "/dashboard/capabilities", icon: Wrench, salesHidden: true },
      { label: "CTA 管理", href: "/dashboard/ctas", icon: MousePointerClick, requiredFeature: "dynamic_cta", salesHidden: true },
      // Redirect 規則 / Entity 關聯 屬系統層操作，僅 admin/owner
      { label: "Redirect 規則", href: "/dashboard/redirects", icon: Link2, requiredFeature: "seo_redirects", adminOnly: true },
      { label: "Entity 關聯", href: "/dashboard/relations", icon: Link2, adminOnly: true },
      { label: "Legacy Site Intake", href: "/dashboard/intake", icon: ClipboardList, adminOnly: true },
    ],
  },
  {
    title: "系統管理",
    items: [
      { label: "通知設定", href: "/dashboard/settings/notifications", icon: Settings },
      { label: "團隊成員", href: "/dashboard/users", icon: Users, adminOnly: true },
      { label: "網站外觀", href: "/dashboard/settings/site-profile", icon: Globe, adminOnly: true },
      { label: "整合設定", href: "/dashboard/integrations", icon: Plug, adminOnly: true },
      { label: "方案與帳單", href: "/dashboard/settings/billing", icon: Settings, adminOnly: true },
    ],
  },
];

function getInitials(email: string) {
  return email.split("@")[0].slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const { state, logout } = useAuth();
  const { hasFeature, isLoading: planLoading } = usePlan();

  const user = state.status === "authenticated" ? state.user : null;
  const canManageSystem = user?.role === "admin" || user?.role === "owner";
  const isSales = user?.role === "sales";
  const roleLabel =
    user?.role === "owner" ? "帳號擁有者" :
    user?.role === "admin" ? "管理員" :
    user?.role === "marketing_manager" ? "行銷經理" :
    user?.role === "sales" ? "業務人員" :
    "一般使用者";
  const accountSettingsHref = canManageSystem ? "/dashboard/users" : "/dashboard";
  const [expandedItems, setExpandedItems] = useState<string[]>([]);
  const [advancedCollapsed, setAdvancedCollapsed] = useState(true);
  // Agent 佇列僅在 AgentOS 服務可連線時顯示（未部署時自動隱藏，避免無效入口）
  // null = 尚未確認，先不渲染，避免「先出現再消失」的閃爍
  const [agentOsOnline, setAgentOsOnline] = useState<boolean | null>(null);

  useEffect(() => {
    let cancelled = false;
    agentosApi.listRuns()
      .then(() => { if (!cancelled) setAgentOsOnline(true); })
      .catch(() => { if (!cancelled) setAgentOsOnline(false); });
    return () => { cancelled = true; };
  }, []);

  function isActive(item: NavItem) {
    if (item.exact) return pathname === item.href;
    return pathname === item.href || pathname.startsWith(item.href + "/");
  }

  /** Returns true if the item is locked (feature required but unavailable). */
  function isLocked(item: NavItem | NavSubItem): boolean {
    if (!item.requiredFeature) return false;
    if (planLoading) return false; // optimistic: don't lock while loading
    return !hasFeature(item.requiredFeature);
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
              const isAdvanced = group.title === "內容與網站基建";
              const visible = group.items.filter((i) =>
                (!i.adminOnly || canManageSystem) && (!i.salesHidden || !isSales)
                && !(i.href === "/dashboard/agent-runs" && agentOsOnline !== true)
              );
              if (!visible.length) return null;
              // Auto-expand 內容與網站基建 if any child is active
              const anyAdvancedActive = isAdvanced && visible.some(item =>
                pathname === item.href || pathname.startsWith(item.href + "/")
              );
              const showAdvanced = !isAdvanced || anyAdvancedActive || !advancedCollapsed;
              return (
                <div key={group.title}>
                  <div className="flex items-center justify-between mb-1 px-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-[hsl(var(--sidebar-foreground))]/40">
                      {group.title}
                    </p>
                    {isAdvanced && (
                      <button
                        onClick={() => setAdvancedCollapsed(v => !v)}
                        className="flex h-4 w-4 items-center justify-center text-[hsl(var(--sidebar-foreground))]/30 hover:text-[hsl(var(--sidebar-foreground))]/70 transition-colors"
                        aria-label={advancedCollapsed && !anyAdvancedActive ? "展開" : "收合"}
                      >
                        <ChevronRight className={cn("h-3 w-3 transition-transform duration-200", showAdvanced && "rotate-90")} />
                      </button>
                    )}
                  </div>
                  {showAdvanced && (
                  <ul className="space-y-0.5">
                    {visible.map((item) => {
                      const active = isActive(item);
                      const locked = isLocked(item);
                      const Icon = item.icon;
                      const hasChildren = !!item.children?.length;
                      const visibleChildren = item.children?.filter(c =>
                        (!c.adminOnly || canManageSystem) && (!c.salesHidden || !isSales)
                      ) ?? [];
                      const anyChildActive = visibleChildren.some(c => pathname === c.href || pathname.startsWith(c.href + "/"));
                      const isExpanded = anyChildActive || expandedItems.includes(item.href);
                      return (
                        <li key={item.href}>
                          <div className={cn("flex items-center", hasChildren && "gap-0.5 pr-1")}>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                {locked ? (
                                  /* ── Locked item — not navigable ── */
                                  <Link
                                    href="/dashboard/settings/billing"
                                    className={cn(
                                      "group flex flex-1 items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150",
                                      "text-[hsl(var(--sidebar-foreground))]/35 hover:bg-[hsl(var(--sidebar-accent))]/50 hover:text-[hsl(var(--sidebar-foreground))]/50"
                                    )}
                                  >
                                    <Icon className="h-4 w-4 shrink-0 text-[hsl(var(--sidebar-foreground))]/25" />
                                    <span className="truncate flex-1">{item.label}</span>
                                    <Lock className="h-3 w-3 shrink-0 text-[hsl(var(--sidebar-foreground))]/30" />
                                  </Link>
                                ) : (
                                  /* ── Normal / active item ── */
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
                                )}
                              </TooltipTrigger>
                              <TooltipContent side="right" className="text-xs">
                                {locked ? "升級至 Professional 方案解鎖" : item.label}
                              </TooltipContent>
                            </Tooltip>
                            {hasChildren && !locked && (
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
                          {hasChildren && !locked && isExpanded && visibleChildren.length > 0 && (
                            <ul className="mt-0.5 ml-[22px] space-y-0.5 border-l border-white/10 pl-3">
                              {visibleChildren.map(child => {
                                const childLocked = isLocked(child);
                                const childActive = !childLocked && (pathname === child.href || pathname.startsWith(child.href + "/"));
                                const ChildIcon = child.icon;
                                return (
                                  <li key={child.href}>
                                    {childLocked ? (
                                      <Link
                                        href="/dashboard/settings/billing"
                                        className="flex items-center gap-2 rounded-md px-2 py-1.5 text-xs font-medium text-[hsl(var(--sidebar-foreground))]/30 hover:bg-[hsl(var(--sidebar-accent))]/50 transition-all duration-150"
                                      >
                                        <ChildIcon className="h-3.5 w-3.5 shrink-0 text-[hsl(var(--sidebar-foreground))]/20" />
                                        <span className="truncate flex-1">{child.label}</span>
                                        <Lock className="h-3 w-3 shrink-0 text-[hsl(var(--sidebar-foreground))]/20" />
                                      </Link>
                                    ) : (
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
                                    )}
                                  </li>
                                );
                              })}
                            </ul>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                  )}
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
                      {roleLabel}
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
                  <Link href={accountSettingsHref} className="flex items-center gap-2 cursor-pointer">
                    <Settings className="h-4 w-4" />
                    帳號設定
                  </Link>
                </DropdownMenuItem>
                <DropdownMenuItem asChild>
                  <Link href="/dashboard/settings/notifications" className="flex items-center gap-2 cursor-pointer">
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
