"use client";

import { useEffect, useState } from "react";
import { Menu } from "lucide-react";
import { usePathname } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/lib/auth/store";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { state } = useAuth();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [tenantBrand, setTenantBrand] = useState({ name: "ForgeBase", mark: "FB" });
  const accessToken = state.status === "authenticated" ? state.accessToken : null;

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!accessToken) return;
    let cancelled = false;
    fetch(`${API_BASE}/site-profile`, { headers: buildApiHeaders(accessToken) })
      .then(async (response) => response.ok ? response.json() : null)
      .then((profile: { brand_name?: string; logo_mark?: string } | null) => {
        if (!cancelled && profile?.brand_name) {
          setTenantBrand({
            name: profile.brand_name,
            mark: profile.logo_mark || profile.brand_name.slice(0, 2).toUpperCase(),
          });
        }
      })
      .catch(() => undefined);
    return () => { cancelled = true; };
  }, [accessToken]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <div className="hidden shrink-0 lg:block">
        <Sidebar />
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent
          side="left"
          className="w-[min(15rem,calc(100vw-1rem))] border-0 p-0 [&>button]:z-10 [&>button]:text-white"
        >
          <SheetTitle className="sr-only">後台功能選單</SheetTitle>
          <SheetDescription className="sr-only">
            選擇要前往的後台功能頁面。
          </SheetDescription>
          <Sidebar />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-background px-4 lg:hidden">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="開啟功能選單"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-[10px] font-bold text-primary-foreground">
              {tenantBrand.mark}
            </div>
            <div className="leading-tight">
              <p className="max-w-[14rem] truncate text-sm font-semibold">{tenantBrand.name}</p>
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">ForgeBase</p>
            </div>
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto bg-muted/30 p-4 pb-24 sm:p-6 sm:pb-24">
          {children}
        </main>
      </div>
    </div>
  );
}
