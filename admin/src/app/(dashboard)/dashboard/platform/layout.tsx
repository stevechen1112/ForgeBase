"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";

/** Platform super-admin section gate — redirects non-superusers */
export default function PlatformLayout({ children }: { children: React.ReactNode }) {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "unauthenticated") {
      router.replace("/login");
    } else if (state.status === "authenticated" && !state.user?.is_superuser) {
      router.replace("/dashboard");
    }
  }, [state, router]);

  if (state.status !== "authenticated" || !state.user?.is_superuser) return null;
  return <>{children}</>;
}
