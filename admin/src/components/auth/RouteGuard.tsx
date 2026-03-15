"use client";
/**
 * RouteGuard — 包裹需要認證的頁面。
 * - Loading 時顯示 spinner。
 * - Unauthenticated 時 redirect 到 /login。
 * - Authenticated 但 role 不符時顯示 403。
 */
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import type { UserRead } from "@/lib/api/auth";

type Props = {
  children: React.ReactNode;
  allowedRoles?: UserRead["role"][];
};

export function RouteGuard({ children, allowedRoles }: Props) {
  const { state } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (state.status === "unauthenticated") {
      router.replace("/login");
    }
  }, [state.status, router]);

  if (state.status === "loading") {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
      </div>
    );
  }

  if (state.status === "unauthenticated") {
    return null; // redirect in progress
  }

  if (allowedRoles && !allowedRoles.includes(state.user.role)) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-2 text-gray-600">
        <span className="text-4xl font-bold">403</span>
        <p>您沒有權限存取此頁面。</p>
      </div>
    );
  }

  return <>{children}</>;
}
