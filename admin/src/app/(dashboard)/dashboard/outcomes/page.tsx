"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  RefreshCw,
  TrendingUp,
  Clock,
  Filter,
  FileText,
  Lightbulb,
} from "lucide-react";
import { apiClient } from "@/lib/api/client";

// 客戶成果首屏五項（實效計畫 §6.1）＋業務漏斗（§6.3）
type Outcomes = {
  period: { month_start: string; prev_month_start: string };
  qualified_rfq: { this_month: number; prev_month: number };
  first_response: {
    avg_hours: number | null;
    sla_rate_pct: number | null;
    responded: number;
  };
  funnel_status: Record<string, number>;
  top_source_pages: { source_page: string; rfq_count: number }[];
  next_week_suggestions: string[];
};

type FunnelLayer = {
  layer: string;
  label: string;
  count: number;
  cohort: "visitor" | "rfq";
  conversion_from_prev_pct: number | null;
};
type Funnel = {
  days: number;
  methodology: string;
  layers: FunnelLayer[];
  bottleneck_layer: string | null;
};

// 訪客意圖分佈快照（原「行銷漏斗」頁獨有資料，2026-08 併入本頁）
type IntentStageRow = { stage: string; visitors: number };
type VisitorFunnel = {
  funnel_stages: IntentStageRow[];
  totals: { visitors: number };
};

type NorthStarLayer = {
  stage: string;
  label: string;
  count: number;
  previous_count: number | null;
  conversion_from_previous_pct: number | null;
  drop_off: number | null;
};
type NorthStarFunnel = {
  days: number;
  cohort: string;
  warning: string;
  layers: NorthStarLayer[];
  attribution: Record<string, { count: number; won_revenue: string }>;
};
type RateMetric = {
  numerator: number;
  denominator: number;
  rate_pct: number | null;
};
type NorthStarQuality = {
  days: number;
  metrics: Record<string, RateMetric>;
  note: string;
};
type ControlledAutoReadiness = {
  evaluation_only: boolean;
  gate_passed: boolean;
  activation_available: boolean;
  blockers: string[];
  metrics: Record<string, RateMetric>;
};

const STAGE_LABEL: Record<string, string> = {
  cold: "初次瀏覽",
  warm: "多次互動",
  hot: "高度關注",
  sales_ready: "可成交",
};
const STAGE_COLOR: Record<string, string> = {
  cold: "bg-blue-500",
  warm: "bg-yellow-500",
  hot: "bg-orange-500",
  sales_ready: "bg-red-500",
};

// Intent facet 成交迴路觀察（§8.3）：成交訪客 vs 全體 RFQ 訪客的 facet 輪廓 lift
type FacetFeedback = {
  facet: string;
  avg_all_rfq_visitors: number;
  avg_won_visitors: number;
  won_lift: number | null;
  hint: string;
};
type OutcomeFeedback = {
  sample:
    | {
        rfq_with_snapshot: number;
        won: number;
        legacy_without_snapshot: number;
      }
    | number;
  statistically_actionable: boolean;
  minimum_sample: { rfq: number; won: number };
  facets: FacetFeedback[];
  note: string;
};

const FACET_LABEL: Record<string, string> = {
  product_interest: "產品興趣",
  trust_validation: "信任驗證",
  procurement_readiness: "採購準備度",
  urgency: "急迫性",
};

const STATUS_ORDER = [
  "new",
  "assigned",
  "in_progress",
  "quoted",
  "negotiation",
  "won",
  "lost",
  "expired",
];
const STATUS_LABEL: Record<string, string> = {
  new: "新進",
  assigned: "已指派",
  in_progress: "處理中",
  quoted: "已報價",
  negotiation: "談判中",
  won: "成交",
  lost: "流失",
  expired: "過期",
};

export default function OutcomesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [outcomes, setOutcomes] = useState<Outcomes | null>(null);
  const [funnel, setFunnel] = useState<Funnel | null>(null);
  const [visitorFunnel, setVisitorFunnel] = useState<VisitorFunnel | null>(
    null,
  );
  const [feedback, setFeedback] = useState<OutcomeFeedback | null>(null);
  const [northStar, setNorthStar] = useState<NorthStarFunnel | null>(null);
  const [northStarQuality, setNorthStarQuality] =
    useState<NorthStarQuality | null>(null);
  const [autoReadiness, setAutoReadiness] =
    useState<ControlledAutoReadiness | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [o, f, fb, vf, ns, quality, readiness] = await Promise.all([
        apiClient.get<Outcomes>("/tracking/outcomes", token),
        apiClient.get<Funnel>("/tracking/funnel?days=30", token),
        apiClient
          .get<OutcomeFeedback>("/tracking/intent/outcome-feedback", token)
          .catch(() => null),
        apiClient
          .get<VisitorFunnel>("/tracking/analytics/funnel?days=30", token)
          .catch(() => null),
        apiClient
          .get<NorthStarFunnel>("/tracking/growth-funnel?days=30", token)
          .catch(() => null),
        apiClient
          .get<NorthStarQuality>(
            "/tracking/growth-funnel/quality?days=30",
            token,
          )
          .catch(() => null),
        apiClient
          .get<ControlledAutoReadiness>(
            "/tracking/controlled-auto/readiness?days=30",
            token,
          )
          .catch(() => null),
      ]);
      setOutcomes(o);
      setFunnel(f);
      setFeedback(fb);
      setVisitorFunnel(vf);
      setNorthStar(ns);
      setNorthStarQuality(quality);
      setAutoReadiness(readiness);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const qualifiedDelta = outcomes
    ? outcomes.qualified_rfq.this_month - outcomes.qualified_rfq.prev_month
    : 0;
  const maxFunnelCount = funnel
    ? Math.max(...funnel.layers.map((l) => l.count), 1)
    : 1;
  const maxNorthStarCount = northStar
    ? Math.max(...northStar.layers.map((l) => l.count), 1)
    : 1;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">成果總覽</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            本月合格詢價、回覆速度，以及內容帶來的詢價與成交來源
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw
            className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
          />
          重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* 首屏五項（§6.1） */}
      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-5">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">本月合格詢價</p>
            <p className="mt-2 text-3xl font-bold">
              {outcomes?.qualified_rfq.this_month ?? "—"}
            </p>
            <p
              className={`text-xs ${qualifiedDelta >= 0 ? "text-emerald-600" : "text-red-500"}`}
            >
              {qualifiedDelta >= 0 ? "▲" : "▼"} {Math.abs(qualifiedDelta)} vs
              上月（{outcomes?.qualified_rfq.prev_month ?? "—"}）
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">平均首回時間</p>
            <p className="mt-2 text-3xl font-bold">
              {outcomes?.first_response.avg_hours != null
                ? `${outcomes.first_response.avg_hours}h`
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              已回覆 {outcomes?.first_response.responded ?? 0} 件
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">回覆時效達成率</p>
            <p className="mt-2 text-3xl font-bold">
              {outcomes?.first_response.sla_rate_pct != null
                ? `${outcomes.first_response.sla_rate_pct}%`
                : "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              買家時區工作時間計時
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">成交（本月漏斗）</p>
            <p className="mt-2 text-3xl font-bold">
              {funnel?.layers.find((l) => l.layer === "won")?.count ?? "—"}
            </p>
            <p className="text-xs text-muted-foreground">
              瓶頸層：{funnel?.bottleneck_layer ?? "—"}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">本月 RFQ 來源頁</p>
            <p className="mt-2 text-3xl font-bold">
              {outcomes?.top_source_pages.length ?? 0}
            </p>
            <p className="text-xs text-muted-foreground">可追溯內容歸因</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" />
              北極星閉環（近 {northStar?.days ?? 30} 天）
            </CardTitle>
            <p className="text-xs text-muted-foreground">
              同一批新訪客的匿名追蹤 → 公司 → 窗口 → 外聯 → 回覆 → 接手 →
              RFQ／成交；每層都顯示實際樣本數。
            </p>
          </CardHeader>
          <CardContent>
            {!northStar ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                閉環歸因尚未對此租戶開放或尚無資料
              </p>
            ) : (
              <div className="space-y-4">
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  {northStar.layers.map((layer) => (
                    <div key={layer.stage} className="rounded-lg border p-3">
                      <div className="flex items-center justify-between gap-3 text-sm">
                        <span>{layer.label}</span>
                        <span className="font-bold">{layer.count}</span>
                      </div>
                      <div className="mt-2 h-2 overflow-hidden rounded bg-muted">
                        <div
                          className="h-full bg-primary/70"
                          style={{
                            width: `${Math.max(layer.count ? 3 : 0, (layer.count / maxNorthStarCount) * 100)}%`,
                          }}
                        />
                      </div>
                      <p className="mt-1 text-xs text-muted-foreground">
                        前一步轉換{" "}
                        {layer.conversion_from_previous_pct != null
                          ? `${layer.conversion_from_previous_pct}%`
                          : "—"}
                        {layer.drop_off != null
                          ? ` · 流失 ${layer.drop_off}`
                          : ""}
                      </p>
                    </div>
                  ))}
                </div>
                <div className="grid gap-3 md:grid-cols-4">
                  {Object.entries(northStar.attribution).map(
                    ([kind, value]) => (
                      <div key={kind} className="rounded-lg bg-muted/60 p-3">
                        <p className="text-xs uppercase text-muted-foreground">
                          {kind}
                        </p>
                        <p className="text-xl font-bold">{value.count}</p>
                        <p className="text-xs text-muted-foreground">
                          成交金額 {value.won_revenue}
                        </p>
                      </div>
                    ),
                  )}
                </div>
                <Alert>
                  <AlertDescription className="text-xs">
                    {northStar.warning}
                  </AlertDescription>
                </Alert>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              品質、樣本與 Controlled Auto Gate
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {northStarQuality ? (
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                {Object.entries(northStarQuality.metrics).map(
                  ([key, metric]) => (
                    <div key={key} className="rounded-lg border p-3">
                      <p className="break-words text-xs text-muted-foreground">
                        {key}
                      </p>
                      <p className="text-lg font-bold">
                        {metric.rate_pct != null ? `${metric.rate_pct}%` : "—"}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {metric.numerator} / {metric.denominator}
                      </p>
                    </div>
                  ),
                )}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">尚無閉環品質資料</p>
            )}
            <Alert
              variant={autoReadiness?.gate_passed ? "default" : "destructive"}
            >
              <AlertDescription>
                Controlled Auto 目前僅供評估，無法啟用或自動寄信。
                {autoReadiness
                  ? ` 未通過條件：${autoReadiness.blockers.length ? autoReadiness.blockers.join("、") : "無"}`
                  : " 此租戶尚未開放評估。"}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>

        {/* 業務漏斗：流量 → 成交（§6.3） */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Filter className="h-4 w-4 text-primary" />
              訪客與詢價階段（近 {funnel?.days ?? 30} 天）
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {funnel?.layers.map((layer) => (
              <div
                key={layer.layer}
                className={`flex items-center gap-3 ${layer.layer === "rfq" ? "mt-4 border-t pt-4" : ""}`}
              >
                <span className="w-28 shrink-0 text-sm">{layer.label}</span>
                <div className="h-5 flex-1 overflow-hidden rounded bg-muted">
                  <div
                    className={`h-full ${funnel.bottleneck_layer === layer.layer ? "bg-red-400" : "bg-primary/70"}`}
                    style={{
                      width: `${Math.max(2, (layer.count / maxFunnelCount) * 100)}%`,
                    }}
                  />
                </div>
                <span className="w-14 text-right text-sm font-bold">
                  {layer.count}
                </span>
                <span className="w-16 text-right text-xs text-muted-foreground">
                  {layer.conversion_from_prev_pct != null
                    ? `${layer.conversion_from_prev_pct}%`
                    : "—"}
                </span>
              </div>
            ))}
            <p className="pt-2 text-xs text-muted-foreground">
              訪客與詢價是兩組不同母體，因此不顯示不可靠的「訪客 →
              詢價」轉換率；合格詢價是品質分支，也不與已報價直接相除。
            </p>
            {funnel?.bottleneck_layer && (
              <p className="pt-2 text-xs text-red-500">
                瓶頸層：
                {
                  funnel.layers.find((l) => l.layer === funnel.bottleneck_layer)
                    ?.label
                }{" "}
                — 優先改善此層轉化
              </p>
            )}
          </CardContent>
        </Card>

        {/* RFQ 狀態漏斗（§6.1-3） */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" />
              RFQ 狀態漏斗（目前快照）
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {STATUS_ORDER.map((s) => (
                <div
                  key={s}
                  className="rounded-lg border px-3 py-2 text-center"
                >
                  <p className="text-lg font-bold">
                    {outcomes?.funnel_status[s] ?? 0}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {STATUS_LABEL[s]}
                  </p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* 內容來源歸因（§6.2） */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileText className="h-4 w-4 text-primary" />
              本月 RFQ 來源頁 Top 5
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!outcomes?.top_source_pages.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                本月尚無帶來源的 RFQ
              </p>
            ) : (
              <div className="max-w-full overflow-x-auto">
                <table className="w-full min-w-[480px] text-sm">
                  <tbody className="divide-y">
                    {outcomes.top_source_pages.map((s) => (
                      <tr key={s.source_page}>
                        <td className="max-w-[320px] truncate py-2 pr-3 font-mono text-xs">
                          {s.source_page}
                        </td>
                        <td className="py-2 text-right">
                          <Badge variant="secondary">{s.rfq_count} 件</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* 下週建議（§6.1-5） */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Lightbulb className="h-4 w-4 text-amber-500" />
              下週建議
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {outcomes?.next_week_suggestions.map((s, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Clock className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <span>{s}</span>
                </li>
              ))}
            </ul>
            <div className="mt-4">
              <Button asChild variant="outline" size="sm">
                <Link href="/dashboard/tasks">前往今日待辦 →</Link>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 訪客意圖分佈（原行銷漏斗頁，併入） */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Filter className="h-4 w-4 text-primary" />
              訪客意圖分佈（目前快照）
            </CardTitle>
            <p className="text-xs text-muted-foreground mt-0.5">
              各關注階段的訪客人數，反映累積行為得分；想看個別訪客請前往「買家關注度」
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {!visitorFunnel?.funnel_stages?.length ? (
              <p className="py-4 text-center text-sm text-muted-foreground">
                尚無訪客追蹤資料
              </p>
            ) : (
              visitorFunnel.funnel_stages.map((s) => {
                const total = Math.max(visitorFunnel.totals?.visitors ?? 0, 1);
                const maxV = Math.max(
                  ...visitorFunnel.funnel_stages.map((x) => x.visitors),
                  1,
                );
                const pct = Math.round((s.visitors / total) * 100);
                return (
                  <div key={s.stage} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{STAGE_LABEL[s.stage] ?? s.stage}</span>
                      <span className="font-medium">
                        {s.visitors}{" "}
                        <span className="text-xs text-muted-foreground">
                          ({pct}%)
                        </span>
                      </span>
                    </div>
                    <div className="h-5 w-full rounded bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded ${STAGE_COLOR[s.stage] ?? "bg-gray-500"} transition-all`}
                        style={{ width: `${(s.visitors / maxV) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })
            )}
          </CardContent>
        </Card>

        {/* 成交迴路觀察：Intent Facet Lift（§8.3） */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" />
              成交迴路觀察
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!feedback || !feedback.facets?.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                {feedback?.note ?? "尚無連結訪客的 RFQ，無法計算"}
              </p>
            ) : (
              <>
                <div className="max-w-full overflow-x-auto">
                  <table className="w-full min-w-[680px] text-sm">
                    <thead>
                      <tr className="text-left text-xs text-muted-foreground">
                        <th className="py-1.5 pr-3">面向</th>
                        <th className="py-1.5 pr-3 text-right">
                          全體 RFQ 訪客均值
                        </th>
                        <th className="py-1.5 pr-3 text-right">成交訪客均值</th>
                        <th className="py-1.5 pr-3 text-right">Lift</th>
                        <th className="py-1.5">建議</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y">
                      {feedback.facets.map((f) => (
                        <tr key={f.facet}>
                          <td className="py-2 pr-3 font-medium">
                            {FACET_LABEL[f.facet] ?? f.facet}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {f.avg_all_rfq_visitors}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {f.avg_won_visitors}
                          </td>
                          <td className="py-2 pr-3 text-right">
                            {f.won_lift != null ? (
                              <Badge
                                variant={
                                  f.won_lift >= 1.5 ? "default" : "secondary"
                                }
                              >
                                {f.won_lift}x
                              </Badge>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                —
                              </span>
                            )}
                          </td>
                          <td className="py-2 text-xs text-muted-foreground">
                            {f.hint}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p className="pt-3 text-xs text-muted-foreground">
                  樣本：
                  {typeof feedback.sample === "object"
                    ? `${feedback.sample.rfq_with_snapshot} 件有意圖快照的 RFQ、${feedback.sample.won} 件成交`
                    : "0"}
                  ・{feedback.note}
                </p>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
