"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard, LogOut, ChevronUp, Bell, Settings, Globe, MessageSquare,
  Lock, ListChecks, ClipboardList, ExternalLink, LifeBuoy, MailCheck,
  Users, Route, PanelsTopLeft,
} from "lucide-react";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type NavItem = {
  label: string;
  href: string;
  icon: React.ElementType;
  adminOnly?: boolean;
  /** Hidden from sales role (visible to marketing_manager, owner, admin). */
  salesHidden?: boolean;
  exact?: boolean;
  /** Deep routes represented by this workspace hub. */
  activePrefixes?: string[];
  badge?: string;
  /** Capability key used for operational availability. */
  requiredFeature?: string;
  hideWhenUnavailable?: boolean;
};

type NavGroup = { title: string; items: NavItem[] };

const NAV_GROUPS: NavGroup[] = [
  {
    title: "核心工作",
    items: [
      { label: "每日營運總覽", href: "/dashboard", icon: LayoutDashboard, exact: true },
      { label: "買家管線", href: "/dashboard/buyers", icon: Route, activePrefixes: ["/dashboard/outcomes", "/dashboard/visitors"] },
      { label: "詢價案件", href: "/dashboard/rfqs", icon: ClipboardList },
      { label: "買家回信與接手", href: "/dashboard/replies", icon: MailCheck, requiredFeature: "inbound_reply", hideWhenUnavailable: true },
      { label: "今日待辦", href: "/dashboard/tasks", icon: ListChecks },
    ],
  },
  {
    title: "官網營運",
    items: [
      { label: "AI 客服對話", href: "/dashboard/chats", icon: MessageSquare, requiredFeature: "chat_handoff", hideWhenUnavailable: true },
      { label: "內容中心", href: "/dashboard/content", icon: PanelsTopLeft, activePrefixes: ["/dashboard/products", "/dashboard/categories", "/dashboard/pages", "/dashboard/settings/site-copy", "/dashboard/assets", "/dashboard/applications", "/dashboard/faqs", "/dashboard/certifications", "/dashboard/capabilities", "/dashboard/comparisons", "/dashboard/redirects"] },
      { label: "潛在買家跟進", href: "/dashboard/growth", icon: MailCheck, salesHidden: true, activePrefixes: ["/dashboard/content-performance", "/dashboard/segments", "/dashboard/ctas", "/dashboard/nurture"] },
    ],
  },
  {
    title: "帳號與支援",
    items: [
      { label: "通知中心", href: "/dashboard/notifications", icon: Bell },
      { label: "團隊成員", href: "/dashboard/users", icon: Users, adminOnly: true },
      { label: "公司與網站資料", href: "/dashboard/settings/site-profile", icon: Globe, adminOnly: true },
      { label: "網站修改與支援", href: "/dashboard/support", icon: LifeBuoy },
    ],
  },
];

function getInitials(email: string) {
  return email.split("@")[0].slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const { state, logout } = useAuth();
  const { hasFeature, isLoading: capabilityLoading } = useCapabilities();

  const user = state.status === "authenticated" ? state.user : null;
  const accessToken = state.status === "authenticated" ? state.accessToken : null;
  const canManageSystem = user?.role === "admin" || user?.role === "owner";
  const isSales = user?.role === "sales";
  const roleLabel =
    user?.role === "owner" ? "帳號擁有者" :
    user?.role === "admin" ? "管理員" :
    user?.role === "marketing_manager" ? "行銷經理" :
    user?.role === "sales" ? "業務人員" :
    "一般使用者";
  const accountSettingsHref = canManageSystem ? "/dashboard/users" : "/dashboard";
  const [tenantBrand, setTenantBrand] = useState({ name: "ForgeBase", mark: "FB", siteUrl: "" });

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    fetch(`${API_BASE}/site-profile`, { headers: buildApiHeaders(accessToken) })
      .then(async (response) => response.ok ? response.json() : null)
      .then((profile: { brand_name?: string; logo_mark?: string; site_url?: string } | null) => {
        if (!cancelled && profile?.brand_name) {
          setTenantBrand({
            name: profile.brand_name,
            mark: profile.logo_mark || profile.brand_name.slice(0, 2).toUpperCase(),
            siteUrl: profile.site_url || "",
          });
        }
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [accessToken]);

  function isActive(item: NavItem) {
    if (item.exact) return pathname === item.href;
    return pathname === item.href
      || pathname.startsWith(item.href + "/")
      || Boolean(item.activePrefixes?.some((prefix) => pathname === prefix || pathname.startsWith(prefix + "/")));
  }

  /** Returns true if the item is locked (feature required but unavailable). */
  function isLocked(item: NavItem): boolean {
    if (!item.requiredFeature) return false;
    if (capabilityLoading) return false; // optimistic: don't lock while loading
    return !hasFeature(item.requiredFeature);
  }

  return (
    <TooltipProvider delayDuration={300}>
      <aside className="flex h-screen w-60 flex-col bg-[hsl(var(--sidebar-background))] text-[hsl(var(--sidebar-foreground))]">
        {/* ─── Logo ─── */}
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-white/10 px-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[hsl(var(--sidebar-primary))] text-xs font-bold text-white shadow-sm">
            {tenantBrand.mark}
          </div>
          <div className="min-w-0 flex flex-col leading-none">
            <span className="truncate text-[15px] font-semibold tracking-tight text-white">{tenantBrand.name}</span>
            <span className="text-[10px] font-medium uppercase tracking-widest text-[hsl(var(--sidebar-foreground))]/40">
              ForgeBase
            </span>
          </div>
        </div>

        {tenantBrand.siteUrl && (
          <a href={tenantBrand.siteUrl} target="_blank" rel="noreferrer" className="mx-3 mt-3 flex items-center justify-center gap-2 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-xs font-medium text-white/80 hover:bg-white/10 hover:text-white">
            <ExternalLink className="h-3.5 w-3.5" />查看公開網站
          </a>
        )}

        {/* ─── Nav ─── */}
        <ScrollArea className="flex-1 px-2 py-3">
          <nav className="space-y-5">
            {NAV_GROUPS.map((group) => {
              const visible = group.items.filter((i) =>
                (!i.adminOnly || canManageSystem) && (!i.salesHidden || !isSales)
                && !(i.hideWhenUnavailable && !capabilityLoading && !hasFeature(i.requiredFeature || ""))
              );
              if (!visible.length) return null;
              return (
                <div key={group.title}>
                  <div className="mb-1 px-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-[hsl(var(--sidebar-foreground))]/40">
                      {group.title}
                    </p>
                  </div>
                  <ul className="space-y-0.5">
                    {visible.map((item) => {
                      const active = isActive(item);
                      const locked = isLocked(item);
                      const Icon = item.icon;
                      return (
                        <li key={item.href}>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              {locked ? (
                                <Link
                                  href={item.href}
                                  className={cn(
                                    "group flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150",
                                    "text-[hsl(var(--sidebar-foreground))]/35 hover:bg-[hsl(var(--sidebar-accent))]/50 hover:text-[hsl(var(--sidebar-foreground))]/50"
                                  )}
                                >
                                  <Icon className="h-4 w-4 shrink-0 text-[hsl(var(--sidebar-foreground))]/25" />
                                  <span className="truncate flex-1">{item.label}</span>
                                  <Lock className="h-3 w-3 shrink-0 text-[hsl(var(--sidebar-foreground))]/30" />
                                </Link>
                              ) : (
                                <Link
                                  href={item.href}
                                  className={cn(
                                    "group flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150",
                                    active
                                      ? "bg-[hsl(var(--sidebar-primary))]/15 text-white"
                                      : "text-[hsl(var(--sidebar-foreground))]/70 hover:bg-[hsl(var(--sidebar-accent))] hover:text-white"
                                  )}
                                >
                                  <Icon className={cn("h-4 w-4 shrink-0 transition-colors", active ? "text-[hsl(var(--sidebar-primary))]" : "text-[hsl(var(--sidebar-foreground))]/50 group-hover:text-white")} />
                                  <span className="truncate">{item.label}</span>
                                  {active && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-[hsl(var(--sidebar-primary))]" />}
                                  {item.badge && (
                                    <Badge variant="secondary" className="ml-auto h-4 px-1.5 text-[10px]">{item.badge}</Badge>
                                  )}
                                </Link>
                              )}
                            </TooltipTrigger>
                            <TooltipContent side="right" className="text-xs">
                              {locked ? "此功能尚未開通" : item.label}
                            </TooltipContent>
                          </Tooltip>
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
