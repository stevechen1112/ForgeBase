"use client";
/**
 * PlanGate — feature flag gating component.
 *
 * Usage (page-level wall):
 *   <PlanGate feature="chat_handoff">
 *     <ChatPage />
 *   </PlanGate>
 *
 * Usage (inline / feature-level UX):
 *   <PlanGate feature="notifications" inline>
 *     <NotificationsSection />
 *   </PlanGate>
 *
 * Usage (inline with custom fallback):
 *   <PlanGate feature="dynamic_cta" inline fallback={<UpgradeChip />}>
 *     <CtaEditor />
 *   </PlanGate>
 */
import Link from "next/link";
import { Lock, ArrowUpRight } from "lucide-react";
import { usePlan } from "@/lib/hooks/usePlan";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

// ── Feature label map ─────────────────────────────────────────────────────────
export const FEATURE_LABELS: Record<string, string> = {
  multilingual: "多語進度",
  ai_content_generation: "AI 文案優化",
  full_tracking: "訪客與成效追蹤",
  intent_scoring: "買家關注度",
  dynamic_cta: "行動按鈕",
  ai_advisor: "AI 產品顧問",
  chat_handoff: "官網對話",
  notifications: "即時通知",
  follow_up_reminders: "跟進提醒",
  nurture_email: "跟進郵件",
  seo_redirects: "舊網址轉址",
};

export function featureLabel(key: string): string {
  return FEATURE_LABELS[key] ?? key;
}

// ── Props ─────────────────────────────────────────────────────────────────────
interface PlanGateProps {
  /** Feature key from PLAN_MATRIX */
  feature: string;
  children: React.ReactNode;
  /**
   * inline=true: renders nothing (or fallback) instead of the full upgrade wall.
   * Use for feature-level UX differences within a page.
   */
  inline?: boolean;
  /** Custom content to show when feature is locked (used with inline). */
  fallback?: React.ReactNode;
}

// ── Component ─────────────────────────────────────────────────────────────────
export function PlanGate({ feature, children, inline, fallback }: PlanGateProps) {
  const { hasFeature, isLoading } = usePlan();

  // While plan is loading, render children optimistically to avoid flicker
  if (isLoading) return <>{children}</>;

  if (hasFeature(feature)) return <>{children}</>;

  // Inline mode: render custom fallback or nothing
  if (inline) return fallback ? <>{fallback}</> : null;

  // Page-level: render full upgrade wall
  return <UpgradeWall feature={feature} />;
}

// ── Upgrade wall (full-page) ───────────────────────────────────────────────────
function UpgradeWall({ feature }: { feature: string }) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-6 text-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted border">
        <Lock className="h-7 w-7 text-muted-foreground" />
      </div>
      <div className="space-y-2 max-w-md">
        <div className="flex items-center justify-center gap-2 mb-1">
          <h2 className="text-xl font-semibold">此功能需要 Professional 方案</h2>
          <Badge variant="secondary" className="text-xs">Professional</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          升級至 Professional 方案以解鎖{" "}
          <span className="font-medium text-foreground">{featureLabel(feature)}</span>
          {" "}功能，以及全套行銷分析與 AI 工具。
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Button asChild>
          <Link href="/dashboard/settings/billing" className="flex items-center gap-1.5">
            查看方案與升級
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href="/dashboard">返回儀表板</Link>
        </Button>
      </div>
    </div>
  );
}

// ── Upgrade chip (inline teaser) ──────────────────────────────────────────────
/**
 * A small inline badge that links to billing.
 * Use as the `fallback` prop for inline PlanGate.
 *
 * Example:
 *   <PlanGate feature="notifications" inline fallback={<UpgradeChip />}>
 */
export function UpgradeChip({ label = "升級解鎖" }: { label?: string }) {
  return (
    <Link
      href="/dashboard/settings/billing"
      className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 hover:bg-amber-100 transition-colors dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-400"
    >
      <Lock className="h-3 w-3" />
      {label}
    </Link>
  );
}
