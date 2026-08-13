"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { PlatformShell } from "@/components/layout/PlatformShell";

/**
 * Authenticated platform pages layout.
 * Redirects to /platform/login if not authenticated or not superuser.
 */
export default function PlatformPagesLayout({ children }: { children: React.ReactNode }) {
  const { state } = usePlatformAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "unauthenticated") {
      router.replace("/platform/login");
    } else if (state.status === "authenticated" && !state.user?.is_superuser) {
      router.replace("/platform/login");
    }
  }, [state, router]);

  if (state.status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center bg-[hsl(222,47%,11%)]">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-red-500 border-t-transparent" />
      </div>
    );
  }

  if (state.status !== "authenticated" || !state.user?.is_superuser) {
    return null;
  }

  return <PlatformShell>{children}</PlatformShell>;
}
