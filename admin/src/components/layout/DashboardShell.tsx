"use client";

import { useEffect, useRef, useState } from "react";
import { usePathname } from "next/navigation";

import { ContextNavigation, resolveDashboardTrail } from "@/components/layout/context-navigation";
import { DashboardTopbar } from "@/components/layout/DashboardTopbar";
import { Sidebar } from "@/components/layout/Sidebar";
import { Sheet, SheetContent, SheetDescription, SheetTitle } from "@/components/ui/sheet";

export function DashboardShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const mainRef = useRef<HTMLElement>(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [desktopNavOpen, setDesktopNavOpen] = useState(true);

  useEffect(() => {
    setMobileNavOpen(false);
    mainRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [pathname]);

  return (
    <div className="flex h-screen overflow-hidden bg-[#f3f5f7]">
      {desktopNavOpen && <div className="hidden shrink-0 lg:block"><Sidebar /></div>}

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-[min(304px,calc(100vw-1rem))] border-0 p-0 [&>button]:z-10 [&>button]:text-white">
          <SheetTitle className="sr-only">後台功能選單</SheetTitle>
          <SheetDescription className="sr-only">選擇工作區或搜尋所有後台功能。</SheetDescription>
          <Sidebar />
        </SheetContent>
      </Sheet>

      <div className="flex min-w-0 flex-1 flex-col">
        <DashboardTopbar onOpenMenu={() => {
          if (window.matchMedia("(min-width: 1024px)").matches) setDesktopNavOpen((open) => !open);
          else setMobileNavOpen(true);
        }} />
        <main ref={mainRef} className="min-w-0 flex-1 overflow-x-hidden overflow-y-auto bg-[#f3f5f7] px-4 pb-24 pt-5 sm:px-6 lg:px-8">
          <div className="mx-auto w-full max-w-[1680px]">
            <ContextNavigation trail={resolveDashboardTrail(pathname)} />
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
