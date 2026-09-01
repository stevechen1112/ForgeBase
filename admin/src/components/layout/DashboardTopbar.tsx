"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { Bell, ChevronRight, Grid2X2, Lock, Menu, Plus, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { WORKSPACES, findCurrentItem, findWorkspace, isRoleAllowed } from "@/lib/navigation/workspaces";
import { cn } from "@/lib/utils";

export function DashboardTopbar({ onOpenMenu }: { onOpenMenu: () => void }) {
  const pathname = usePathname();
  const { state } = useAuth();
  const { hasFeature, isLoading } = useCapabilities();
  const [finderOpen, setFinderOpen] = useState(false);
  const [directoryOpen, setDirectoryOpen] = useState(false);
  const [query, setQuery] = useState("");
  const role = state.status === "authenticated" ? state.user.role : null;
  const canEdit = role === "owner" || role === "admin" || role === "marketing_manager";
  const workspace = findWorkspace(pathname);
  const currentItem = findCurrentItem(pathname);

  const visibleWorkspaces = useMemo(() => WORKSPACES.filter((item) => isRoleAllowed(item.roles, role)), [role]);
  const visibleItems = useMemo(
    () => visibleWorkspaces.flatMap((area) => area.items.filter((item) => isRoleAllowed(item.roles, role)).map((item) => ({ ...item, workspaceLabel: area.label }))),
    [role, visibleWorkspaces],
  );
  const normalizedQuery = query.trim().toLocaleLowerCase("zh-TW");
  const results = normalizedQuery
    ? visibleItems.filter((item) => [item.label, item.description, item.workspaceLabel, ...(item.keywords ?? [])].join(" ").toLocaleLowerCase("zh-TW").includes(normalizedQuery))
    : visibleItems.slice(0, 8);

  useEffect(() => {
    function handleShortcut(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setFinderOpen(true);
      }
    }
    window.addEventListener("keydown", handleShortcut);
    return () => window.removeEventListener("keydown", handleShortcut);
  }, []);

  useEffect(() => {
    setFinderOpen(false);
    setDirectoryOpen(false);
    setQuery("");
  }, [pathname]);

  const itemLocked = (feature?: string) => Boolean(feature && !isLoading && !hasFeature(feature));

  return (
    <>
      <header className="z-30 flex h-[72px] shrink-0 items-center gap-3 border-b border-slate-200 bg-white px-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] sm:px-6">
        <Button type="button" variant="outline" size="icon" className="h-11 w-11" onClick={onOpenMenu} aria-label="顯示或收合功能選單"><Menu className="h-5 w-5" /></Button>

        <nav aria-label="目前位置" className="hidden min-w-0 items-center gap-2 text-sm lg:flex">
          <Link href={workspace.href} className="max-w-40 truncate font-semibold text-slate-800 hover:text-[#176c89]">{workspace.label}</Link>
          {currentItem && currentItem.href !== workspace.href && <><ChevronRight className="h-4 w-4 text-slate-400" /><span className="max-w-52 truncate text-slate-500">{currentItem.label}</span></>}
        </nav>

        <button type="button" onClick={() => setFinderOpen(true)} className="mx-auto flex h-11 min-w-0 max-w-xl flex-1 items-center gap-3 rounded-lg border border-slate-300 bg-slate-50 px-3 text-left text-sm text-slate-500 transition hover:border-[#4aa7be] hover:bg-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[#176c89] lg:mx-4">
          <Search className="h-4 w-4 shrink-0" /><span className="truncate">搜尋所有後台功能</span><kbd className="ml-auto hidden rounded border bg-white px-1.5 py-0.5 text-[11px] text-slate-400 sm:inline">Ctrl K</kbd>
        </button>

        <span className="hidden rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-700 xl:inline">外銷主管模式</span>
        <Button type="button" variant="outline" className="hidden h-11 gap-2 sm:inline-flex" onClick={() => setDirectoryOpen(true)}><Grid2X2 className="h-4 w-4" />全部功能</Button>
        <Button asChild variant="ghost" size="icon" className="h-11 w-11" aria-label="開啟通知中心"><Link href="/dashboard/notifications"><Bell className="h-5 w-5" /></Link></Button>
        {canEdit && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild><Button className="h-11 bg-[#176c89] px-4 hover:bg-[#115a73]"><Plus className="h-4 w-4" /><span className="hidden sm:inline">快速新增</span></Button></DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel>選擇要新增的內容</DropdownMenuLabel><DropdownMenuSeparator />
              <DropdownMenuItem asChild><Link href="/dashboard/products/new" className="min-h-10 cursor-pointer">新增商品</Link></DropdownMenuItem>
              <DropdownMenuItem asChild><Link href="/dashboard/pages/new" className="min-h-10 cursor-pointer">新增頁面</Link></DropdownMenuItem>
              <DropdownMenuItem asChild><Link href="/dashboard/segments/new" className="min-h-10 cursor-pointer">新增跟進名單</Link></DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </header>

      <Dialog open={finderOpen} onOpenChange={setFinderOpen}>
        <DialogContent className="top-[42%] max-h-[80vh] max-w-2xl overflow-hidden p-0">
          <DialogHeader className="border-b p-5 pb-4">
            <DialogTitle>搜尋所有後台功能</DialogTitle>
            <DialogDescription>輸入工作目的或功能名稱；未開通功能仍會顯示並清楚標示。</DialogDescription>
            <div className="relative pt-2"><Search className="absolute left-3 top-[1.35rem] h-5 w-5 text-slate-400" /><Input autoFocus value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：報價、產品、圖片、跟進" className="h-12 pl-11 text-base" /></div>
          </DialogHeader>
          <div className="max-h-[50vh] overflow-y-auto p-3">
            {results.map((item) => {
              const Icon = item.icon;
              const locked = itemLocked(item.feature);
              return <Link key={`${item.workspaceLabel}-${item.href}-${item.label}`} href={item.href} className="group flex min-h-16 items-center gap-4 rounded-lg px-3 py-2 hover:bg-slate-50"><span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-[#176c89]"><Icon className="h-5 w-5" /></span><span className="min-w-0 flex-1"><span className="block font-semibold text-slate-800">{item.label}</span><span className="block truncate text-sm text-slate-500">{item.workspaceLabel}・{item.description}</span></span>{locked ? <span className="flex items-center gap-1 text-xs font-medium text-amber-700"><Lock className="h-3.5 w-3.5" />未開通</span> : <ChevronRight className="h-4 w-4 text-slate-400 group-hover:text-[#176c89]" />}</Link>;
            })}
            {results.length === 0 && <p className="py-10 text-center text-sm text-slate-500">找不到相符功能，請改用較短的關鍵字。</p>}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={directoryOpen} onOpenChange={setDirectoryOpen}>
        <DialogContent className="max-h-[88vh] max-w-5xl overflow-y-auto">
          <DialogHeader><DialogTitle>全部功能</DialogTitle><DialogDescription>依工作目的整理，而不是把功能藏起來。共 {visibleWorkspaces.length} 個工作區、{visibleItems.length} 個可見入口。</DialogDescription></DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {visibleWorkspaces.map((area) => {
              const Icon = area.icon;
              return <section key={area.id} className="rounded-xl border bg-slate-50/60 p-4"><div className="mb-3 flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#176c89] text-white"><Icon className="h-5 w-5" /></span><div><h3 className="text-base font-bold text-slate-900">{area.label}</h3><p className="mt-1 text-xs leading-5 text-slate-500">{area.description}</p></div></div><div className="space-y-1">{area.items.filter((item) => isRoleAllowed(item.roles, role)).map((item) => { const locked = itemLocked(item.feature); return <Link key={`${area.id}-${item.href}-${item.label}`} href={item.href} className={cn("flex min-h-10 items-center rounded-md px-2 text-sm font-medium hover:bg-white hover:text-[#176c89]", locked ? "text-slate-500" : "text-slate-700")}><span className="truncate">{item.label}</span>{locked ? <Lock className="ml-auto h-3.5 w-3.5 text-amber-600" /> : <ChevronRight className="ml-auto h-3.5 w-3.5 text-slate-400" />}</Link>; })}</div></section>;
            })}
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
