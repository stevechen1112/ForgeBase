"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Lock } from "lucide-react";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { featureLabel } from "@/components/capabilities/CapabilityGate";
import { Button } from "@/components/ui/button";

const FEATURE_ROUTES: { path: string; feature: string }[] = [
  { path: "/dashboard/settings/notifications", feature: "notifications" },
  { path: "/dashboard/pages/new", feature: "advanced_content" },
  { path: "/dashboard/content-performance", feature: "full_tracking" },
  { path: "/dashboard/visitors", feature: "full_tracking" },
  { path: "/dashboard/segments", feature: "audience_segments" },
  { path: "/dashboard/nurture", feature: "nurture_email" },
  { path: "/dashboard/comparisons", feature: "advanced_content" },
  { path: "/dashboard/ctas", feature: "dynamic_cta" },
  { path: "/dashboard/redirects", feature: "seo_redirects" },
  { path: "/dashboard/chats", feature: "chat_handoff" },
];

function routeMatches(pathname: string, base: string) {
  return pathname === base || pathname.startsWith(`${base}/`);
}

export function FeatureAccessGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { hasFeature, isLoading } = useCapabilities();
  const requirement = FEATURE_ROUTES.find((item) => routeMatches(pathname, item.path));

  if (!requirement) return <>{children}</>;
  if (isLoading) {
    return (
      <div className="flex min-h-[65vh] items-center justify-center">
        <div className="h-7 w-7 animate-spin rounded-full border-4 border-primary border-t-transparent" />
      </div>
    );
  }
  if (hasFeature(requirement.feature)) return <>{children}</>;
  const retirementObservation = requirement.feature === "ai_relation_recommendations";

  return (
    <div className="flex min-h-[65vh] flex-col items-center justify-center gap-4 px-6 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full border bg-muted">
        <Lock className="h-6 w-6 text-muted-foreground" />
      </div>
      <div>
        <h1 className="text-xl font-semibold">{retirementObservation ? "此入口已停用" : "此租戶尚未開通這項功能"}</h1>
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {retirementObservation
            ? `${featureLabel(requirement.feature)}已進入正式退場觀察，不接受租戶或系統管理員臨時開通。核心資料契約與既有成果仍會保留。`
            : `${featureLabel(requirement.feature)}不在目前的導入範圍；如需展示或測試，可由 ForgeBase 系統管理員開通。`}
        </p>
      </div>
      <Button asChild variant="outline"><Link href="/dashboard">返回每日營運總覽</Link></Button>
    </div>
  );
}
