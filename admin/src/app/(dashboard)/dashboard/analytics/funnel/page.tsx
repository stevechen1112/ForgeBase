"use client";
/**
 * Funnel Analytics Dashboard
 * /dashboard/analytics/funnel
 *
 * Shows marketing funnel: visitors by intent stage, RFQ by status, conversion rates.
 */
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { apiClient } from "@/lib/api/client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type FunnelStage = { stage: string; visitors: number };
type FunnelData = {
  period_days: number;
  funnel_stages: FunnelStage[];
  rfq_by_status: Record<string, number>;
  totals: { visitors: number; rfqs: number; won: number };
  conversion_rates: { visitor_to_rfq: number; rfq_to_won: number; visitor_to_won: number };
};

const STAGE_LABELS: Record<string, string> = {
  cold: "初次瀏覽",
  warm: "多次互動",
  hot: "高度關注",
  sales_ready: "可成交",
};

const STAGE_COLORS: Record<string, string> = {
  cold: "bg-blue-500",
  warm: "bg-yellow-500",
  hot: "bg-orange-500",
  sales_ready: "bg-red-500",
};

const RFQ_STATUS_LABELS: Record<string, string> = {
  new: "新詢價",
  assigned: "已指派",
  in_progress: "處理中",
  quoted: "已報價",
  won: "成交",
  lost: "未成交",
  expired: "過期",
};

export default function FunnelDashboard() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [days, setDays] = useState(30);
  const [data, setData] = useState<FunnelData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    apiClient
      .get<FunnelData>(`/tracking/analytics/funnel?days=${days}`, token)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, days]);

  const maxVisitors = data ? Math.max(...(data.funnel_stages ?? []).map((s) => s.visitors), 1) : 1;
  const total_visitors = data ? data.totals?.visitors ?? 0 : 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">行銷漏斗</h1>
          <p className="mt-1 text-sm text-muted-foreground">可視化訪客從到訪、互動到 RFQ 詢價的完整轉換漏斗</p>
        </div>
        <select
          className="rounded-md border px-3 py-1.5 text-sm"
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
        >
          <option value={7}>最近 7 天</option>
          <option value={30}>最近 30 天</option>
          <option value={90}>最近 90 天</option>
        </select>
      </div>

      {loading && <p className="text-muted-foreground">載入中…</p>}

      {data && (
        <>
          {/* Conversion rate cards */}
          <div className="grid grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">訪客 → 詢價</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.conversion_rates.visitor_to_rfq}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.totals.visitors} 訪客 → {data.totals.rfqs} 詢價
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">詢價 → 成交</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.conversion_rates.rfq_to_won}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.totals.rfqs} 詢價 → {data.totals.won} 成交
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground">訪客 → 成交</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{data.conversion_rates.visitor_to_won}%</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {data.totals.visitors} 訪客 → {data.totals.won} 成交
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Intent stage distribution */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">訪客意圖分佈</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                目前各意圖階段的訪客人數快照，反映訪客累積行為得分（非線性漏斗）
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.funnel_stages.map((s) => {
                const pct = total_visitors > 0 ? Math.round(s.visitors / total_visitors * 100) : 0;
                return (
                  <div key={s.stage} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span>{STAGE_LABELS[s.stage] || s.stage}</span>
                      <span className="font-medium">{s.visitors} <span className="text-xs text-muted-foreground">({pct}%)</span></span>
                    </div>
                    <div className="h-6 w-full rounded bg-muted overflow-hidden">
                      <div
                        className={`h-full rounded ${STAGE_COLORS[s.stage] || "bg-gray-500"} transition-all`}
                        style={{ width: `${(s.visitors / maxVisitors) * 100}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* RFQ by status */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">詢價單狀態分佈</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {Object.entries(data.rfq_by_status).map(([status, count]) => (
                  <div key={status} className="rounded-lg border p-3 text-center">
                    <p className="text-2xl font-bold">{count}</p>
                    <p className="text-xs text-muted-foreground">{RFQ_STATUS_LABELS[status] || status}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
