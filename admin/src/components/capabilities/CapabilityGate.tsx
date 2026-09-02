"use client";
/**
 * CapabilityGate — access control for the single ForgeBase product.
 *
 * Usage (page-level wall):
 *   <CapabilityGate feature="chat_handoff">
 *     <ChatPage />
 *   </CapabilityGate>
 *
 * Usage (inline / feature-level UX):
 *   <CapabilityGate feature="notifications" inline>
 *     <NotificationsSection />
 *   </CapabilityGate>
 *
 * Usage (inline with custom fallback):
 *   <CapabilityGate feature="dynamic_cta" inline fallback={<CapabilityBadge />}>
 *     <CtaEditor />
 *   </CapabilityGate>
 */
import Link from "next/link";
import { Lock } from "lucide-react";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { Button } from "@/components/ui/button";

// ── Feature label map ─────────────────────────────────────────────────────────
export const FEATURE_LABELS: Record<string, string> = {
  multilingual: "多語內容（來源語言 + 客戶語言草稿）",
  full_tracking: "訪客與成效追蹤",
  dynamic_cta: "行動按鈕",
  ai_advisor: "AI 產品顧問",
  chat_handoff: "官網對話",
  notifications: "即時通知",
  seo_redirects: "舊網址轉址",
  advanced_content: "進階頁面與比較內容",
  company_identification: "企業辨識與聯絡人候選",
};

export function featureLabel(key: string): string {
  return FEATURE_LABELS[key] ?? key;
}

// ── Props ─────────────────────────────────────────────────────────────────────
interface CapabilityGateProps {
  /** Feature key from the server-side capability catalog. */
  feature: string;
  children: React.ReactNode;
  /**
   * inline=true: renders nothing (or fallback) instead of the full unavailable view.
   * Use for feature-level UX differences within a page.
   */
  inline?: boolean;
  /** Custom content to show when feature is locked (used with inline). */
  fallback?: React.ReactNode;
}

// ── Component ─────────────────────────────────────────────────────────────────
export function CapabilityGate({ feature, children, inline, fallback }: CapabilityGateProps) {
  const { hasFeature, isLoading } = useCapabilities();

  // Render optimistically while access is loading to avoid layout flicker.
  if (isLoading) return <>{children}</>;

  if (hasFeature(feature)) return <>{children}</>;

  // Inline mode: render custom fallback or nothing
  if (inline) return fallback ? <>{fallback}</> : null;

  // Page-level: explain that the capability is outside the current operating scope.
  return <CapabilityUnavailable feature={feature} />;
}

// ── Unavailable capability (full-page) ─────────────────────────────────────────
function CapabilityUnavailable({ feature }: { feature: string }) {
  return (
    <div className="flex h-full min-h-[60vh] flex-col items-center justify-center gap-6 text-center px-4">
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-muted border">
        <Lock className="h-7 w-7 text-muted-foreground" />
      </div>
      <div className="space-y-2 max-w-md">
        <div className="flex items-center justify-center gap-2 mb-1">
          <h2 className="text-xl font-semibold">此功能尚未納入目前導入範圍</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{featureLabel(feature)}</span>
          {" "}屬於依測試與導入範圍另外確認的功能，目前不影響已交付的網站內容與詢價工作。
        </p>
      </div>
      <Button variant="outline" asChild>
        <Link href="/dashboard">返回儀表板</Link>
      </Button>
    </div>
  );
}

// ── Inline availability badge ─────────────────────────────────────────────────
/**
 * Use as the `fallback` prop for an inline CapabilityGate.
 *
 * Example:
 *   <CapabilityGate feature="notifications" inline fallback={<CapabilityBadge />}>
 */
export function CapabilityBadge({ label = "依導入範圍開放" }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-amber-300 bg-amber-50 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:border-amber-700 dark:bg-amber-950/30 dark:text-amber-400">
      <Lock className="h-3 w-3" />
      {label}
    </span>
  );
}
