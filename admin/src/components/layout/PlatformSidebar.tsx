"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  ShieldAlert, Building2, Users, Activity, ClipboardCheck, KanbanSquare, ScanSearch, ContactRound, MailCheck,
  FileStack, ListChecks, ServerCog, BarChart3, ScrollText, ArchiveX,
  LogOut, ChevronUp, LayoutDashboard,
} from "lucide-react";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

const NAV_GROUPS = [
  {
    label: "工作台",
    items: [
      { label: "平台總覽", href: "/platform/overview", icon: LayoutDashboard },
      { label: "營運待辦", href: "/platform/workspace", icon: ListChecks },
    ],
  },
  {
    label: "導入與交付",
    items: [
      { label: "導入申請", href: "/platform/applications", icon: ClipboardCheck },
      { label: "租戶管理", href: "/platform/tenants", icon: Building2 },
      { label: "網站交付", href: "/platform/delivery", icon: KanbanSquare },
      { label: "範本中心", href: "/platform/templates", icon: FileStack },
    ],
  },
  {
    label: "日常營運",
    items: [
      { label: "全平台詢價", href: "/platform/rfqs", icon: ClipboardCheck },
      { label: "公司推測", href: "/platform/company-identification", icon: ScanSearch },
      { label: "聯絡窗口候選", href: "/platform/contact-enrichment", icon: ContactRound },
      { label: "外聯草稿審核", href: "/platform/outreach", icon: MailCheck },
      { label: "系統健康", href: "/platform/health", icon: Activity },
    ],
  },
  {
    label: "資源與治理",
    items: [
      { label: "外部服務與資料", href: "/platform/resources", icon: ServerCog },
      { label: "用量", href: "/platform/usage", icon: BarChart3 },
      { label: "平台用戶", href: "/platform/users", icon: Users },
      { label: "操作紀錄", href: "/platform/audit", icon: ScrollText },
      { label: "功能退場稽核", href: "/platform/retirement", icon: ArchiveX },
    ],
  },
];

function getInitials(email: string) {
  return email.split("@")[0].slice(0, 2).toUpperCase();
}

export function PlatformSidebar() {
  const pathname = usePathname();
  const { state, logout } = usePlatformAuth();
  const user = state.status === "authenticated" ? state.user : null;

  function isActive(href: string) {
    return pathname === href || pathname.startsWith(href + "/");
  }

  return (
    <aside className="flex h-screen w-60 flex-col bg-[hsl(222,47%,11%)] text-gray-300">
      {/* ─── Logo ─── */}
      <div className="flex h-14 shrink-0 items-center gap-3 border-b border-white/10 px-4">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-600 text-xs font-bold text-white shadow-sm">
          <ShieldAlert className="h-4 w-4" />
        </div>
        <div className="flex flex-col leading-none">
          <span className="text-[15px] font-semibold tracking-tight text-white">ForgeBase</span>
          <span className="text-[10px] font-medium uppercase tracking-widest text-red-400/60">
            Platform Admin
          </span>
        </div>
      </div>

      {/* ─── Nav ─── */}
      <ScrollArea className="flex-1 px-2 py-4">
        <nav className="space-y-5">
          {NAV_GROUPS.map((group) => (
            <section key={group.label}>
              <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-red-400/50">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {group.items.map(({ label, href, icon: Icon }) => {
                  const active = isActive(href);
                  return (
                    <li key={href}>
                      <Link
                        href={href}
                        className={cn(
                          "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-all duration-150",
                          active ? "bg-red-500/15 text-white" : "text-gray-400 hover:bg-red-500/10 hover:text-white",
                        )}
                      >
                        <Icon className={cn("h-4 w-4 shrink-0 transition-colors", active ? "text-red-400" : "text-gray-500")} />
                        <span className="truncate">{label}</span>
                        {active && <div className="ml-auto h-1.5 w-1.5 rounded-full bg-red-400" />}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </nav>
      </ScrollArea>

      {/* ─── User zone ─── */}
      {user && (
        <div className="shrink-0 border-t border-white/10 p-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button className="flex w-full items-center gap-3 rounded-md px-2 py-2 text-left transition-colors hover:bg-white/5 focus:outline-none focus-visible:ring-1 focus-visible:ring-white/20">
                <Avatar className="h-8 w-8 shrink-0">
                  <AvatarFallback className="bg-red-600/20 text-red-400 text-xs font-semibold">
                    {getInitials(user.email)}
                  </AvatarFallback>
                </Avatar>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-white leading-none mb-0.5">
                    {user.email.split("@")[0]}
                  </p>
                  <p className="truncate text-[11px] text-gray-500 leading-none">
                    Super Admin
                  </p>
                </div>
                <ChevronUp className="h-3.5 w-3.5 shrink-0 text-gray-500" />
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
  );
}
