"use client";
import { useEffect, useState, useCallback } from "react";
import {
  TrendingUp, TrendingDown, Users, Package, ClipboardList, DollarSign,
  Globe, Eye, MousePointerClick, Percent, ArrowUpRight,
  RefreshCcw, Download,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/lib/auth/store";
import { API_BASE } from "@/lib/api/client";

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
  won:         { label: "成交", variant: "success" },
  lost:        { label: "未成交", variant: "secondary" },
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

  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [rfqs, setRfqs] = useState<RFQRow[]>([]);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const [funnelRes, rfqRes] = await Promise.all([
        fetch(`${API_BASE}/tracking/analytics/funnel?days=30`, { headers: { Authorization: `Bearer ${token}` } }),
        fetch(`${API_BASE}/tracking/rfqs?limit=5`, { headers: { Authorization: `Bearer ${token}` } }),
      ]);
      const [funnelJson, rfqJson] = await Promise.all([funnelRes.json(), rfqRes.json()]);
      setFunnel(funnelJson);
      setRfqs(Array.isArray(rfqJson) ? rfqJson : []);
    } catch { /* 靜默失敗 */ }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { loadData(); }, [loadData]);

  // ── 衍生數值 ──────────────────────────────────────────────────────────────
  const visitors = funnel?.totals.visitors ?? 0;
  const rfqCount = funnel?.totals.rfqs ?? 0;
  const convRate = funnel?.conversion_rates.visitor_to_rfq ?? 0;
  const newRfqs = funnel?.rfq_by_status["new"] ?? 0;

  const KPI_CARDS = [
    {
      title: "近 30 天詢價 (RFQ)",
      value: loading ? "—" : rfqCount.toLocaleString(),
      sub: `其中 ${newRfqs} 筆待處理`,
      icon: ClipboardList,
      color: "text-blue-500",
      bg: "bg-blue-50",
      real: true,
    },
    {
      title: "近 30 天訪客",
      value: loading ? "—" : visitors.toLocaleString(),
      sub: "追蹤器記錄的不重複訪客",
      icon: Eye,
      color: "text-violet-500",
      bg: "bg-violet-50",
      real: true,
    },
    {
      title: "訪客 → 詢價轉換率",
      value: loading ? "—" : `${convRate}%`,
      sub: `${visitors} 訪客 → ${rfqCount} 詢價`,
      icon: Percent,
      color: "text-amber-500",
      bg: "bg-amber-50",
      real: true,
    },
  ];

  return (
    <div className="space-y-6">
      {/* ─── Header ─── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">儀表板</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            歡迎回來！以下是今日的業務摘要。
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" className="gap-2" onClick={loadData} disabled={loading}>
            <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            重新整理
          </Button>
          <Button variant="outline" size="sm" className="gap-2">
            <Download className="h-3.5 w-3.5" />
            匯出報表
          </Button>
        </div>
      </div>

      {/* ─── KPI Grid（真實資料）─── */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {KPI_CARDS.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.title} className="hover:shadow-card-hover transition-shadow duration-200">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.title}
                </CardTitle>
                <div className={`flex h-9 w-9 items-center justify-center rounded-lg ${kpi.bg}`}>
                  <Icon className={`h-4.5 w-4.5 ${kpi.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold tracking-tight">{kpi.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{kpi.sub}</p>
              </CardContent>
            </Card>
          );
        })}
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
              <a href="/backend/dashboard/rfqs">查看全部 <ArrowUpRight className="h-3.5 w-3.5" /></a>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="py-8 text-center text-sm text-muted-foreground">載入中…</p>
            ) : rfqs.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">尚無詢價資料</p>
            ) : (
              <div className="divide-y">
                {rfqs.map((rfq) => {
                  const cfg = STATUS_CONFIG[rfq.status] ?? { label: rfq.status, variant: "secondary" as const };
                  return (
                    <div key={rfq.id} className="flex items-center gap-4 px-6 py-3.5 hover:bg-muted/40 transition-colors">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className="text-sm font-medium font-mono text-foreground">{rfq.rfq_number}</span>
                          <Badge variant={cfg.variant} className="shrink-0 text-[10px] h-4 px-1.5">{cfg.label}</Badge>
                          {rfq.priority === "high" && (
                            <Badge variant="destructive" className="shrink-0 text-[10px] h-4 px-1.5">高優先</Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground">優先級：{rfq.priority === "urgent" ? "緊急" : rfq.priority === "high" ? "高" : rfq.priority === "normal" ? "一般" : rfq.priority}</p>
                      </div>
                      <div className="text-right shrink-0">
                        <p className="text-[11px] text-muted-foreground">{relativeTime(rfq.created_at)}</p>
                      </div>
                    </div>
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
              {funnel && Object.entries(funnel.rfq_by_status).length > 0 ? (
                Object.entries(funnel.rfq_by_status).map(([status, count]) => {
                  const cfg = STATUS_CONFIG[status] ?? { label: status, variant: "secondary" as const };
                  return (
                    <div key={status} className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Badge variant={cfg.variant} className="text-[10px] h-4 px-1.5">{cfg.label}</Badge>
                      </div>
                      <span className="text-sm font-semibold">{count}</span>
                    </div>
                  );
                })
              ) : (
                <p className="text-xs text-muted-foreground py-4 text-center">載入中…</p>
              )}
            </CardContent>
          </Card>

          {/* Quick stats — 標示為參考數據 */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">其他指標</CardTitle>
                <span className="text-[10px] text-muted-foreground border rounded px-1.5 py-0.5">參考數據</span>
              </div>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {[
                { label: "平均回應時間", value: "< 2 小時", icon: RefreshCcw },
                { label: "活躍買家國家", value: "40+", icon: Globe },
                { label: "本月新用戶", value: "156", icon: Users },
                { label: "點擊率 (CTR)", value: "4.2%", icon: MousePointerClick },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">
                    <Icon className="h-3.5 w-3.5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{value}</p>
                    <p className="text-[11px] text-muted-foreground">{label}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

