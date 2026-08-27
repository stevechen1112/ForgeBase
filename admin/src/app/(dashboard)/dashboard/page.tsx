"use client";
import { useEffect, useState, useCallback } from "react";
import {
  ClipboardList,
  Bell, Eye, Percent, ArrowUpRight,
  RefreshCcw, Sunrise, AlertTriangle, Flame,
  ChevronRight, ListChecks, PanelsTopLeft, Route,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { apiClient } from "@/lib/api/client";
import { localeCoverageApi } from "@/lib/api/content";
import Link from "next/link";
import { cn } from "@/lib/utils";

// ── 型別 ────────────────────────────────────────────────────────────────────
type FunnelData = {
  totals: { visitors: number; rfqs: number; won: number };
  conversion_rates: { visitor_to_rfq: number; rfq_to_won: number; visitor_to_won: number };
  rfq_by_status: Record<string, number>;
};
type RFQRow = {
  id: string;
  rfq_number: string;
  status: string;
  priority: string;
  created_at: string;
};

const STATUS_CONFIG: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" | "success" | "warning" | "info" }> = {
  new:         { label: "新進", variant: "info" },
  assigned:    { label: "已指派", variant: "info" },
  in_progress: { label: "處理中", variant: "warning" },
  reviewing:   { label: "審核中", variant: "warning" },
  quoted:      { label: "已報價", variant: "success" },
  negotiation: { label: "談判中", variant: "warning" },
  won:         { label: "成交", variant: "success" },
  lost:        { label: "流失", variant: "secondary" },
  expired:     { label: "過期", variant: "secondary" },
  closed:      { label: "已結案", variant: "secondary" },
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "剛才";
  if (mins < 60) return `${mins} 分鐘前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} 小時前`;
  const days = Math.floor(hrs / 24);
  if (days === 1) return "昨天";
  return `${days} 天前`;
}

export default function DashboardPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const { hasFeature, isLoading: featuresLoading } = useCapabilities();
  const hasFullTracking = !featuresLoading && hasFeature("full_tracking");
  const hasMultilingual = !featuresLoading && hasFeature("multilingual");

  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [rfqs, setRfqs] = useState<RFQRow[]>([]);
  const [localeSummary, setLocaleSummary] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token || featuresLoading) return;
    setLoading(true);
    setError(null);
    try {
      const [funnelResult, rfqResult, coverageResult] = await Promise.allSettled([
        hasFullTracking
          ? apiClient.get<FunnelData>("/tracking/analytics/funnel?days=30", token)
          : Promise.resolve(null),
        apiClient.get<RFQRow[]>("/tracking/rfqs?limit=200", token),
        hasMultilingual ? localeCoverageApi.get(token) : Promise.resolve(null),
      ]);
      if (funnelResult.status === "fulfilled" && funnelResult.value) {
        setFunnel(funnelResult.value);
      } else {
        setFunnel(null);
      }
      if (rfqResult.status === "fulfilled") {
        setRfqs(Array.isArray(rfqResult.value) ? rfqResult.value : []);
      } else {
        setRfqs([]);
        setError(rfqResult.reason instanceof Error ? rfqResult.reason.message : "無法載入 RFQ");
      }
      if (coverageResult.status === "fulfilled" && coverageResult.value) {
        const coverage = coverageResult.value;
        const parts: string[] = [];
        if (coverage.missing > 0) parts.push(`${coverage.missing} 筆缺${coverage.target_locale === "en" ? "英文" : "買方語系"}`);
        if (coverage.draft > 0) parts.push(`${coverage.draft} 筆草稿未上架`);
        if (coverage.stale > 0) parts.push(`${coverage.stale} 筆需更新`);
        setLocaleSummary(parts.length ? parts.join("、") : "買方語系內容已齊");
      } else {
        setLocaleSummary(null);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [featuresLoading, hasFullTracking, hasMultilingual, token]);

  useEffect(() => { loadData(); }, [loadData]);

  // ── 衍生數值 ──────────────────────────────────────────────────────────────
  const visitors = funnel?.totals.visitors ?? 0;
  const convRate = funnel?.conversion_rates.visitor_to_rfq ?? 0;
  const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
  const recentRfqs = rfqs.filter((rfq) => new Date(rfq.created_at).getTime() >= thirtyDaysAgo);
  const rfqCount = recentRfqs.length;
  const newRfqs = recentRfqs.filter((rfq) => rfq.status === "new").length;
  const rfqByStatus = recentRfqs.reduce<Record<string, number>>((counts, rfq) => {
    counts[rfq.status] = (counts[rfq.status] ?? 0) + 1;
    return counts;
  }, {});
  const overdueRfqs = recentRfqs.filter(r => {
    const hrs = (Date.now() - new Date(r.created_at).getTime()) / 3600000;
    return (r.status === "new" || r.status === "assigned") && hrs > 24;
  });
  const userName = user?.email?.split("@")[0] ?? "您";

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* ─── AI 晨報 Hero ─────────────────────────────────────────────── */}
      <div className="relative overflow-hidden rounded-xl bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6 text-white shadow-lg">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/10 via-transparent to-purple-600/10 pointer-events-none" />
        <div className="relative flex flex-wrap items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-amber-400/20 text-amber-400">
              <Sunrise className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold leading-tight">每日營運總覽</h1>
              <p className="text-sm text-white/60 mt-0.5">早安，{userName}！以下是今天需要您關注的事項</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0 gap-1.5 text-white/60 hover:text-white hover:bg-white/10"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCcw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            重新整理
          </Button>
        </div>
        <p className="relative mt-4 text-sm text-white/80 leading-relaxed">
          {loading ? "載入中…" : (
            <>
              近 30 天共 <strong className="text-white">{rfqCount} 筆詢價</strong>
              {overdueRfqs.length > 0 && <>，其中 <strong className="text-red-300">{overdueRfqs.length} 筆逾時未回覆</strong></>}
              {hasFullTracking && visitors > 0 && <>，追蹤到 <strong className="text-white">{visitors} 位訪客</strong></>}
              {hasFullTracking
                ? <>。訪客轉詢價率目前 <strong className="text-amber-300">{convRate}%</strong>。</>
                : <>。請依待辦與案件狀態安排後續處理。</>}
              {localeSummary && (
                <> 買方語系：{localeSummary}。{localeSummary !== "買方語系內容已齊" && (
                  <Link href="/dashboard/products?pair_status=missing_target" className="ml-1 underline decoration-white/40 hover:decoration-white">查看商品</Link>
                )}</>
              )}
            </>
          )}
        </p>
      </div>

      {/* ─── 優先行動卡 ───────────────────────────────────────────────── */}
      {(overdueRfqs.length > 0 || newRfqs > 0) && (
        <div>
          <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">
            🔥 需要您處理的事項
          </p>
          <div className="space-y-2">
            {overdueRfqs.slice(0, 3).map(rfq => (
              <Link
                key={rfq.id}
                href={`/dashboard/rfqs/${rfq.id}`}
                className="flex items-center gap-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 transition-colors hover:bg-red-100 dark:border-red-900/40 dark:bg-red-950/20 dark:hover:bg-red-950/30"
              >
                <AlertTriangle className="h-4 w-4 shrink-0 text-red-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">{rfq.rfq_number}</p>
                  <p className="text-xs text-muted-foreground">
                    逾時 {Math.floor((Date.now() - new Date(rfq.created_at).getTime()) / 3600000)} 小時未回覆
                  </p>
                </div>
                <Badge variant="destructive" className="shrink-0 text-[10px]">逾時</Badge>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            ))}
            {newRfqs > 0 && overdueRfqs.length === 0 && (
              <Link
                href="/dashboard/rfqs"
                className="flex items-center gap-4 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 transition-colors hover:bg-blue-100 dark:border-blue-900/40 dark:bg-blue-950/20"
              >
                <Flame className="h-4 w-4 shrink-0 text-blue-500" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-foreground">有 {newRfqs} 筆新詢價待處理</p>
                  <p className="text-xs text-muted-foreground">點擊前往詢價中心</p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
              </Link>
            )}
          </div>
        </div>
      )}

      {/* ─── KPI Grid（真實資料）─── */}
      <div>
        <p className="mb-3 text-xs font-semibold uppercase tracking-widest text-muted-foreground">📊 營運數據概覽</p>
        <div className={cn("grid grid-cols-1 gap-4", hasFullTracking ? "sm:grid-cols-3" : "sm:grid-cols-1")}>
          {/* RFQ KPI — always available */}
          <Card className="hover:shadow-card-hover transition-shadow duration-200">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">近 30 天詢價 (RFQ)</CardTitle>
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50">
                <ClipboardList className="h-4 w-4 text-blue-500" />
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold tracking-tight">{loading ? "—" : rfqCount.toLocaleString()}</p>
              <p className="mt-1 text-xs text-muted-foreground">其中 {newRfqs} 筆待處理</p>
            </CardContent>
          </Card>

          {/* 只顯示目前可用的訪客與轉換能力，不呈現付費升級語意。 */}
          {hasFullTracking && (
            <Card className="hover:shadow-card-hover transition-shadow duration-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">近 30 天訪客</CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-violet-50">
                  <Eye className="h-4 w-4 text-violet-500" />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tracking-tight">{loading ? "—" : visitors.toLocaleString()}</p>
                <p className="mt-1 text-xs text-muted-foreground">追蹤器記錄的不重複訪客</p>
              </CardContent>
            </Card>
          )}

          {hasFullTracking && (
            <Card className="hover:shadow-card-hover transition-shadow duration-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">訪客 → 詢價轉換率</CardTitle>
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-amber-50">
                  <Percent className="h-4 w-4 text-amber-500" />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tracking-tight">{loading ? "—" : `${convRate}%`}</p>
                <p className="mt-1 text-xs text-muted-foreground">{visitors} 訪客 → {rfqCount} 詢價</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* ─── Main content grid ─── */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Recent RFQs（真實資料）*/}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base">最新詢價單</CardTitle>
              <CardDescription className="text-xs mt-0.5">近 30 天共 {rfqCount} 筆</CardDescription>
            </div>
            <Button variant="ghost" size="sm" className="gap-1.5 text-xs text-primary" asChild>
              <Link href="/dashboard/rfqs">查看全部 <ArrowUpRight className="h-3.5 w-3.5" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">載入中…</p>
            ) : recentRfqs.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無詢價資料</p>
            ) : (
              <div className="divide-y">
                {recentRfqs.slice(0, 8).map((rfq) => {
                  const cfg = STATUS_CONFIG[rfq.status] ?? { label: rfq.status, variant: "secondary" as const };
                  return (
                    <Link
                      key={rfq.id}
                      href={`/dashboard/rfqs/${rfq.id}`}
                      className="flex items-center gap-4 px-6 py-3.5 hover:bg-muted/40 transition-colors"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-medium font-mono text-foreground">{rfq.rfq_number}</span>
                          <Badge variant={cfg.variant} className="shrink-0 text-[10px] h-4 px-1.5">{cfg.label}</Badge>
                          {(rfq.priority === "high" || rfq.priority === "urgent") && (
                            <Badge variant="destructive" className="shrink-0 text-[10px] h-4 px-1.5">高優先</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">{relativeTime(rfq.created_at)}</p>
                      </div>
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground/40" />
                    </Link>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Right column：RFQ 狀態分佈（真實）*/}
        <div className="space-y-6">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">詢價單狀態</CardTitle>
              <CardDescription className="text-xs">近 30 天各狀態數量</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {loading ? (
                <p className="text-xs text-muted-foreground py-4 text-center">載入中…</p>
              ) : Object.entries(rfqByStatus).length > 0 ? (
                Object.entries(rfqByStatus).map(([status, count]) => {
                  const cfg = STATUS_CONFIG[status] ?? { label: status, variant: "secondary" as const };
                  return (
                    <div key={status} className="flex items-center justify-between">
                      <Badge variant={cfg.variant} className="text-[10px] h-4 px-1.5">{cfg.label}</Badge>
                      <span className="text-sm font-semibold">{count}</span>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">近 30 天尚無詢價</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">快速入口</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="space-y-1.5">
              {[
                { label: "買家管線", href: "/dashboard/buyers", icon: Route },
                { label: "內容中心", href: "/dashboard/content", icon: PanelsTopLeft },
                { label: "今日待辦", href: "/dashboard/tasks", icon: ListChecks },
                { label: "通知中心", href: "/dashboard/notifications", icon: Bell },
              ].map(({ label, href, icon: Icon }) => (
                <Link
                  key={label}
                  href={href}
                  className="flex items-center gap-3 rounded-md px-2 py-2 text-sm hover:bg-muted/60 transition-colors"
                >
                  <div className="flex h-7 w-7 items-center justify-center rounded-md bg-muted">
                    <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <span className="text-sm text-foreground">{label}</span>
                  <ChevronRight className="ml-auto h-3.5 w-3.5 text-muted-foreground/40" />
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
