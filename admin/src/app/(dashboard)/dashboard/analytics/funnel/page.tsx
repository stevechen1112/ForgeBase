"use client";
/**
 * Funnel Analytics Dashboard
 * /dashboard/analytics/funnel
 *
 * Shows marketing funnel: visitors by intent stage, RFQ by status, conversion rates.
 */
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth/store";
import { API_BASE } from "@/lib/api/client";
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
  cold: "Cold — 初次瀏覽",
  warm: "Warm — 多次互動",
  hot: "Hot — 高意圖",
  sales_ready: "Sales Ready",
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
    fetch(`${API_BASE}/tracking/analytics/funnel?days=${days}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [token, days]);

  const maxVisitors = data ? Math.max(...data.funnel_stages.map((s) => s.visitors), 1) : 1;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">行銷漏斗分析</h1>
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

          {/* Funnel stages bar chart */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">意圖階段分佈</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {data.funnel_stages.map((s) => (
                <div key={s.stage} className="space-y-1">
                  <div className="flex justify-between text-sm">
                    <span>{STAGE_LABELS[s.stage] || s.stage}</span>
                    <span className="font-medium">{s.visitors}</span>
                  </div>
                  <div className="h-6 w-full rounded bg-muted overflow-hidden">
                    <div
                      className={`h-full rounded ${STAGE_COLORS[s.stage] || "bg-gray-500"} transition-all`}
                      style={{ width: `${(s.visitors / maxVisitors) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
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
