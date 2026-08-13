"use client";
/**
 * RouteGuard — 包裹需要認證的頁面。
 * - Loading 時顯示 spinner。
 * - Unauthenticated 時 redirect 到 /login。
 * - Authenticated 但 role 不符時顯示 403。
 */
import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth/store";
import type { UserRead } from "@/lib/api/auth";
import { Button } from "@/components/ui/button";

type Props = {
  children: React.ReactNode;
  allowedRoles?: UserRead["role"][];
};

export function RouteGuard({ children, allowedRoles }: Props) {
  const { state } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

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

  const adminOnlyRoutes = [
    "/dashboard/ml-scoring",
    "/dashboard/redirects",
    "/dashboard/users",
    "/dashboard/settings/site-profile",
    "/dashboard/integrations",
    "/dashboard/settings/integrations",
    "/dashboard/settings/billing",
  ];
  const salesHiddenRoutes = [
    "/dashboard/intent-rules",
    "/dashboard/content-performance",
    "/dashboard/copilot",
    "/dashboard/agent-runs",
    "/dashboard/segments",
    "/dashboard/nurture",
    "/dashboard/categories",
    "/dashboard/pages",
    "/dashboard/assets",
    "/dashboard/applications",
    "/dashboard/faqs",
    "/dashboard/certifications",
    "/dashboard/capabilities",
    "/dashboard/comparisons",
    "/dashboard/ctas",
  ];
  const matchesRoute = (routes: string[]) => routes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`),
  );
  const canManageSystem = state.user.role === "owner" || state.user.role === "admin";
  const routeDenied =
    (matchesRoute(adminOnlyRoutes) && !canManageSystem)
    || (matchesRoute(salesHiddenRoutes) && state.user.role === "sales");

  if (routeDenied || (allowedRoles && !allowedRoles.includes(state.user.role))) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 px-6 text-center text-gray-600">
        <span className="text-4xl font-bold">403</span>
        <p className="font-medium text-gray-800">您沒有權限使用這項功能</p>
        <p className="max-w-md text-sm">目前帳號角色無法存取此頁面。如需操作，請聯絡帳戶擁有者調整權限。</p>
        <Button asChild variant="outline" size="sm">
          <Link href="/dashboard">返回每日營運總覽</Link>
        </Button>
      </div>
    );
  }

  return <>{children}</>;
}
