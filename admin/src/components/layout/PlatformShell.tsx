"use client";

import { useEffect, useState } from "react";
import { Menu, ShieldAlert } from "lucide-react";
import { usePathname } from "next/navigation";
import { PlatformSidebar } from "@/components/layout/PlatformSidebar";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

export function PlatformShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    setMobileNavOpen(false);
  }, [pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <div className="hidden shrink-0 lg:block">
        <PlatformSidebar />
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent
          side="left"
          className="w-60 border-0 p-0 [&>button]:z-10 [&>button]:text-white"
        >
          <SheetTitle className="sr-only">平台管理功能選單</SheetTitle>
          <PlatformSidebar />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center gap-3 border-b bg-background px-4 lg:hidden">
          <Button
            type="button"
            variant="ghost"
            size="icon"
            aria-label="開啟平台管理選單"
            aria-expanded={mobileNavOpen}
            onClick={() => setMobileNavOpen(true)}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="flex h-7 w-7 items-center justify-center rounded-md bg-red-600 text-white">
              <ShieldAlert className="h-4 w-4" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold">ForgeBase</p>
              <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Platform Admin</p>
            </div>
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-y-auto bg-muted/30 p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
