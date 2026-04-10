"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { usePlan } from "@/lib/hooks/usePlan";
import { strategiesApi, type ContentStrategy } from "@/lib/api/content";
import { UpgradeChip } from "@/components/plan/PlanGate";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Plus, BarChart2 } from "lucide-react";
import { apiClient } from "@/lib/api/client";

const STATUS_LABELS: Record<string, string> = {
  unplanned: "未規劃",
  brief_created: "摘要已建",
  ai_generated: "AI 已生成",
  in_review: "審核中",
  published: "已發布",
};

const STATUS_COLORS: Record<string, string> = {
  unplanned: "bg-muted text-muted-foreground",
  brief_created: "bg-blue-100 text-blue-700",
  ai_generated: "bg-purple-100 text-purple-700",
  in_review: "bg-amber-100 text-amber-700",
  published: "bg-green-100 text-green-700",
};

const TIER_STYLES: Record<string, { badge: string; border: string; label: string }> = {
  strong:  { badge: "bg-green-100 text-green-800",  border: "border-l-4 border-l-green-500", label: "強勢" },
  engaged: { badge: "bg-blue-100 text-blue-700",    border: "border-l-4 border-l-blue-400",  label: "活躍" },
  weak:    { badge: "bg-amber-100 text-amber-700",  border: "border-l-4 border-l-amber-400", label: "微弱" },
  dark:    { badge: "bg-muted text-muted-foreground", border: "",                             label: "無流量" },
};

const PAGE_TYPES = ["product", "application", "category", "faq", "comparison", "certification", "page", "other"];

type StrategyMetric = {
  strategy_id: string;
  page_id: string | null;
  page_title: string | null;
  page_views: number;
  unique_visitors: number;
  rfq_count: number;
  spec_downloads: number;
  avg_intent_score: number;
  performance_tier: "strong" | "engaged" | "weak" | "dark";
};

export default function StrategiesPage() {
  const { state } = useAuth();
  const { hasFeature } = usePlan();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const hasTracking = hasFeature("full_tracking");
  const [all, setAll] = useState<ContentStrategy[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [deleting, setDeleting] = useState<string | null>(null);

  const [showPerf, setShowPerf] = useState(false);
  const [perfDays, setPerfDays] = useState(30);
  const [metricsMap, setMetricsMap] = useState<Record<string, StrategyMetric>>({});
  const [loadingPerf, setLoadingPerf] = useState(false);
  const [tierSummary, setTierSummary] = useState<Record<string, number>>({});

  const load = useCallback(() => {
    strategiesApi.list(token, { page_size: 200 }).then((res) => setAll(res.data));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const loadPerformance = useCallback(async () => {
    if (!token || !hasTracking) return;
    setLoadingPerf(true);
    try {
      const data = await apiClient.get<{ strategies?: StrategyMetric[]; tier_summary?: Record<string, number> }>(
        `/tracking/analytics/strategy-map?days=${perfDays}`,
        token,
      );
      const map: Record<string, StrategyMetric> = {};
      for (const row of data.strategies ?? []) { map[row.strategy_id] = row; }
      setMetricsMap(map);
      setTierSummary(data.tier_summary ?? {});
    } finally { setLoadingPerf(false); }
  }, [token, perfDays, hasTracking]);

  useEffect(() => { if (showPerf) loadPerformance(); }, [showPerf, loadPerformance]);

  const handleDelete = async (id: string) => {
    if (!confirm("確定刪除此策略？")) return;
    setDeleting(id);
    await strategiesApi.delete(token, id);
    load();
    setDeleting(null);
  };

  const rows = filter === "all" ? all : all.filter((s) => s.page_type === filter);
  const byStatus = (["unplanned", "brief_created", "ai_generated", "in_review", "published"] as const).map((status) => ({
    status,
    items: rows.filter((s) => s.status === status),
  }));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">內容策略地圖</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">追蹤每個頁面的內容生命週期狀態</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant={showPerf ? "default" : "outline"}
            size="sm"
            disabled={!hasTracking}
            onClick={() => setShowPerf(!showPerf)}
          >
            <BarChart2 className="mr-1.5 h-4 w-4" />
            {showPerf ? "隱藏成效" : "顯示成效"}
          </Button>
          <Button asChild size="sm">
            <Link href="/dashboard/strategies/new"><Plus className="mr-1.5 h-4 w-4" />新增策略</Link>
          </Button>
        </div>
      </div>

      {/* Performance controls */}
      {!hasTracking && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <div>
            <p className="text-sm font-medium text-amber-900">策略成效覆蓋需要 Professional 方案</p>
            <p className="text-xs text-amber-700 mt-0.5">Starter 仍可管理策略內容，但不提供流量與轉換成效覆蓋。</p>
          </div>
          <UpgradeChip label="升級解鎖策略成效" />
        </div>
      )}

      {showPerf && hasTracking && (
        <div className="flex flex-wrap items-center gap-4 rounded-xl bg-indigo-50 border border-indigo-200 px-4 py-3">
          <span className="text-xs font-medium text-indigo-700">成效時段：</span>
          {[7, 14, 30, 90].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setPerfDays(d)}
              className={`rounded px-2 py-1 text-xs font-medium transition-colors ${
                perfDays === d ? "bg-indigo-600 text-white" : "bg-white text-indigo-600 border border-indigo-300 hover:bg-indigo-50"
              }`}
            >
              {d}天
            </button>
          ))}
          {loadingPerf && <span className="text-xs text-indigo-400 animate-pulse ml-2">載入中…</span>}
          {Object.keys(tierSummary).length > 0 && (
            <div className="flex gap-3 ml-auto">
              {(["strong", "engaged", "weak", "dark"] as const).map((tier) => (
                <span key={tier} className={`text-xs px-2 py-0.5 rounded-full font-medium ${TIER_STYLES[tier].badge}`}>
                  {TIER_STYLES[tier].label} {tierSummary[tier] ?? 0}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex flex-wrap gap-2">
        {["all", ...PAGE_TYPES].map((pt) => (
          <button
            key={pt}
            type="button"
            onClick={() => setFilter(pt)}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === pt ? "bg-primary text-primary-foreground" : "bg-muted text-muted-foreground hover:bg-muted/80"
            }`}
          >
            {pt === "all" ? "全部" : pt} ({pt === "all" ? all.length : all.filter((s) => s.page_type === pt).length})
          </button>
        ))}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-5 gap-3">
        {byStatus.map(({ status, items }) => (
          <div key={status} className={`rounded-xl p-4 text-center ${STATUS_COLORS[status]}`}>
            <p className="text-2xl font-bold">{items.length}</p>
            <p className="text-xs mt-1">{STATUS_LABELS[status]}</p>
          </div>
        ))}
      </div>

      {/* Kanban columns */}
      {rows.length === 0 ? (
        <div className="rounded-xl border-2 border-dashed py-16 text-center text-muted-foreground">
          <p className="text-lg">尚無策略紀錄</p>
          <p className="text-sm mt-1">點擊「新增策略」開始規劃</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-5">
          {byStatus.map(({ status, items }) => (
            <div key={status} className="space-y-2">
              <h3 className={`text-xs font-semibold px-2 py-1 rounded-md text-center ${STATUS_COLORS[status]}`}>
                {STATUS_LABELS[status]} ({items.length})
              </h3>
              {items.map((s) => {
                const perf = metricsMap[s.id];
                const tier = showPerf && perf ? perf.performance_tier : null;
                const tierStyle = tier ? TIER_STYLES[tier] : null;
                return (
                  <Card key={s.id} className={`text-xs shadow-sm ${tierStyle?.border ?? ""}`}>
                    <CardContent className="p-3 space-y-1">
                      <div className="flex items-start justify-between gap-1">
                        <div>
                          <Badge variant="secondary" className="mb-1">{s.page_type}</Badge>
                          {tier && (
                            <span className={`inline-block rounded ml-1 px-1 py-0.5 mb-1 ${tierStyle?.badge}`}>
                              {TIER_STYLES[tier].label}
                            </span>
                          )}
                          {s.entity_type && <p className="font-medium">{s.entity_type}</p>}
                          {s.locale && <p className="text-muted-foreground">{s.locale}</p>}
                        </div>
                      </div>
                      {showPerf && perf && perf.page_views > 0 && (
                        <div className="flex gap-2 text-muted-foreground border-t pt-1">
                          <span title="瀏覽次數">👁 {perf.page_views}</span>
                          <span title="詢價數">📋 {perf.rfq_count}</span>
                          {perf.spec_downloads > 0 && <span title="規格下載">📄 {perf.spec_downloads}</span>}
                        </div>
                      )}
                      {showPerf && perf && perf.page_views === 0 && (
                        <p className="text-muted-foreground/50 border-t pt-1">無流量紀錄</p>
                      )}
                      {s.notes && <p className="text-muted-foreground truncate" title={s.notes}>{s.notes}</p>}
                      <div className="flex gap-2 pt-1">
                        <Link href={`/dashboard/strategies/${s.id}/edit`} className="text-primary hover:underline">編輯</Link>
                        {s.brief_id && (
                          <Link href={`/dashboard/briefs/${s.brief_id}/preview`} className="text-purple-600 hover:underline">預覽</Link>
                        )}
                        <button
                          type="button"
                          onClick={() => handleDelete(s.id)}
                          disabled={deleting === s.id}
                          className="text-destructive hover:underline disabled:opacity-50"
                        >
                          刪除
                        </button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
