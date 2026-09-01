"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ChevronRight, ChevronUp, ExternalLink, Lock, LogOut, Search, Settings, Star } from "lucide-react";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { DEFAULT_FAVORITES, WORKSPACES, isRoleAllowed, isRouteActive } from "@/lib/navigation/workspaces";
import { cn } from "@/lib/utils";

function getInitials(email: string) {
  return email.split("@")[0].slice(0, 2).toUpperCase();
}

export function Sidebar() {
  const pathname = usePathname();
  const { state, logout } = useAuth();
  const { hasFeature, isLoading } = useCapabilities();
  const [query, setQuery] = useState("");
  const [tenantBrand, setTenantBrand] = useState({ name: "ForgeBase", mark: "FB", siteUrl: "" });

  const user = state.status === "authenticated" ? state.user : null;
  const accessToken = state.status === "authenticated" ? state.accessToken : null;
  const role = user?.role ?? null;
  const canManageSystem = role === "admin" || role === "owner";
  const roleLabel = role === "owner" ? "帳號擁有者" : role === "admin" ? "管理員" : role === "marketing_manager" ? "行銷經理" : "業務人員";

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    fetch(`${API_BASE}/site-profile`, { headers: buildApiHeaders(accessToken) })
      .then(async (response) => response.ok ? response.json() : null)
      .then((profile: { brand_name?: string; logo_mark?: string; site_url?: string } | null) => {
        if (!cancelled && profile?.brand_name) {
          setTenantBrand({ name: profile.brand_name, mark: profile.logo_mark || profile.brand_name.slice(0, 2).toUpperCase(), siteUrl: profile.site_url || "" });
        }
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [accessToken]);

  const visibleWorkspaces = useMemo(() => WORKSPACES.filter((workspace) => isRoleAllowed(workspace.roles, role)), [role]);
  const allVisibleItems = useMemo(
    () => visibleWorkspaces.flatMap((workspace) => workspace.items.filter((item) => isRoleAllowed(item.roles, role)).map((item) => ({ ...item, workspaceLabel: workspace.label }))),
    [role, visibleWorkspaces],
  );
  const favorites = DEFAULT_FAVORITES.map((href) => allVisibleItems.find((item) => item.href === href)).filter((item): item is NonNullable<typeof item> => Boolean(item));
  const normalizedQuery = query.trim().toLocaleLowerCase("zh-TW");
  const results = normalizedQuery
    ? allVisibleItems.filter((item) => [item.label, item.description, item.workspaceLabel, ...(item.keywords ?? [])].join(" ").toLocaleLowerCase("zh-TW").includes(normalizedQuery))
    : [];
  const locked = (feature?: string) => Boolean(feature && !isLoading && !hasFeature(feature));

  return (
    <aside className="flex h-screen w-[304px] flex-col bg-[#10243a] text-slate-100">
      <div className="border-b border-white/10 px-[18px] pb-[13px] pt-[18px]">
        <div className="flex items-center gap-3">
          <div className="flex h-[42px] w-[42px] shrink-0 items-center justify-center rounded-[9px] bg-white text-sm font-black text-[#10243a] shadow-sm">{tenantBrand.mark}</div>
          <div className="min-w-0">
            <p className="truncate text-[18px] font-bold leading-tight text-white">{tenantBrand.name}</p>
            <p className="mt-1 text-xs tracking-wide text-slate-300">外銷業務營運系統</p>
          </div>
        </div>
        <div className="mt-4 flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2.5 text-[13px] text-slate-300">
          <span>{visibleWorkspaces.length} 個工作入口</span><strong className="text-white">完整功能找得到</strong>
        </div>
      </div>

      <div className="px-4 pt-4">
        <label className="relative block">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜尋工作或功能" aria-label="搜尋後台功能" className="h-[42px] w-full rounded-[7px] border border-white/10 bg-white/5 pl-10 pr-3 text-sm text-white outline-none placeholder:text-slate-400 focus:border-[#56c3df] focus:ring-2 focus:ring-[#56c3df]/20" />
        </label>
      </div>

      <ScrollArea className="flex-1 px-3 py-4">
        {normalizedQuery ? (
          <nav aria-label="功能搜尋結果">
            <p className="px-3 pb-2 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">搜尋結果・{results.length}</p>
            <div className="space-y-1">
              {results.map((item) => {
                const Icon = item.icon;
                return (
                  <Link key={`${item.workspaceLabel}-${item.href}-${item.label}`} href={item.href} className="group flex min-h-12 items-center gap-3 rounded-lg px-3 py-2 text-sm text-slate-200 hover:bg-white/10 hover:text-white">
                    <Icon className="h-[18px] w-[18px] shrink-0 text-cyan-300" />
                    <span className="min-w-0 flex-1"><span className="block truncate font-medium">{item.label}</span><span className="block truncate text-[11px] text-slate-400">{item.workspaceLabel}</span></span>
                    {locked(item.feature) ? <Lock className="h-3.5 w-3.5 text-amber-300" /> : <ChevronRight className="h-4 w-4 text-slate-500 group-hover:text-white" />}
                  </Link>
                );
              })}
              {results.length === 0 && <p className="px-3 py-6 text-sm leading-6 text-slate-400">找不到相符功能。可改用工作目的或功能名稱搜尋。</p>}
            </div>
          </nav>
        ) : (
          <nav aria-label="後台工作區" className="space-y-5">
            <section>
              <div className="mb-1 flex items-center gap-2 px-3"><Star className="h-3.5 w-3.5 text-amber-300" /><p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">我最常用</p></div>
              <div className="space-y-0.5">
                {favorites.map((item) => {
                  const Icon = item.icon;
                  const active = isRouteActive(pathname, item.href);
                  return <Link key={item.href} href={item.href} className={cn("flex min-h-11 items-center gap-3 rounded-[7px] px-3 py-2 text-[14px] font-semibold", active ? "bg-white text-[#10243a]" : "text-slate-200 hover:bg-white/10 hover:text-white")}><Icon className="h-[18px] w-[18px] shrink-0" /><span className="truncate">{item.label}</span><Star className="ml-auto h-4 w-4 fill-amber-300 text-amber-300" /></Link>;
                })}
              </div>
            </section>

            <section>
              <p className="mb-1 px-3 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">所有工作區・{visibleWorkspaces.length}</p>
              <div className="space-y-1">
                {visibleWorkspaces.map((workspace) => {
                  const Icon = workspace.icon;
                  const active = isRouteActive(pathname, workspace.href) || workspace.items.some((item) => isRouteActive(pathname, item.href));
                  return (
                    <Link key={workspace.id} href={workspace.href} className={cn("group flex min-h-12 items-center gap-3 rounded-[7px] px-3 py-2 text-[15px] font-semibold transition-colors", active ? "bg-white text-[#10243a]" : "text-slate-200 hover:bg-white/5 hover:text-white")}>
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center"><Icon className="h-[18px] w-[18px]" /></span>
                      <span className="truncate">{workspace.shortLabel}</span>
                      <span className={cn("ml-auto rounded-full px-2 py-0.5 text-[11px] font-semibold", active ? "bg-[#e5eff6] text-[#355572]" : "bg-white/10 text-slate-300")}>{workspace.items.filter((item) => isRoleAllowed(item.roles, role)).length}</span>
                    </Link>
                  );
                })}
              </div>
            </section>
          </nav>
        )}
      </ScrollArea>

      {tenantBrand.siteUrl && <a href={tenantBrand.siteUrl} target="_blank" rel="noreferrer" className="mx-4 mb-2 flex min-h-11 items-center justify-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 text-sm font-medium text-slate-200 hover:bg-white/10 hover:text-white"><ExternalLink className="h-4 w-4" />查看公開網站</a>}

      {user && (
        <div className="border-t border-white/10 p-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex min-h-14 w-full items-center gap-3 rounded-lg px-2 text-left hover:bg-white/5 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300">
                <Avatar className="h-9 w-9 shrink-0"><AvatarFallback className="bg-[#176c89] text-xs font-bold text-white">{getInitials(user.email)}</AvatarFallback></Avatar>
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold text-white">{user.full_name || user.email.split("@")[0]}</span><span className="block truncate text-xs text-slate-400">{roleLabel}</span></span>
                <ChevronUp className="h-4 w-4 text-slate-400" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent side="top" align="start" className="mb-1 w-64">
              <DropdownMenuLabel><p className="truncate text-sm">{user.email}</p></DropdownMenuLabel><DropdownMenuSeparator />
              <DropdownMenuItem asChild><Link href={canManageSystem ? "/dashboard/users" : "/dashboard"} className="min-h-10 cursor-pointer gap-2"><Settings className="h-4 w-4" />帳號設定</Link></DropdownMenuItem><DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout} className="min-h-10 cursor-pointer gap-2 text-destructive focus:text-destructive"><LogOut className="h-4 w-4" />登出</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}
    </aside>
  );
}
