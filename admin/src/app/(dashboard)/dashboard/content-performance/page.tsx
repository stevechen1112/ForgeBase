"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FileText, Package, LayoutGrid } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type AnalyticsPage = { slug: string; title?: string; views?: number; unique_visitors?: number; events?: number };
type AnalyticsSummary = { total_events: number; total_pages: number; total_unique_visitors: number };
type AnalyticsResponse = { period_days: number; summary: AnalyticsSummary; pages?: AnalyticsPage[]; products?: AnalyticsPage[]; applications?: AnalyticsPage[] };

type Tab = "pages" | "products" | "applications";
const TABS: { key: Tab; label: string; icon: React.ElementType; endpoint: string }[] = [
  { key: "pages", label: "頁面", icon: FileText, endpoint: "tracking/analytics/pages" },
  { key: "products", label: "商品", icon: Package, endpoint: "tracking/analytics/products" },
  { key: "applications", label: "應用場景", icon: LayoutGrid, endpoint: "tracking/analytics/applications" },
];

export default function ContentPerformancePage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [tab, setTab] = useState<Tab>("pages");
  const [data, setData] = useState<Record<Tab, AnalyticsResponse | null>>({ pages: null, products: null, applications: null });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (t: Tab) => {
    setLoading(true); setError(null);
    try {
      const ep = TABS.find(x => x.key === t)!.endpoint;
      const r = await fetch(`${API_BASE}/${ep}?days=30`, { headers: { Authorization: `Bearer ${token}` } });
      const d = await r.json();
      setData(prev => ({ ...prev, [t]: d }));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { load(tab); }, [load, tab]);

  const cur = data[tab];
  const rows: AnalyticsPage[] = cur ? (cur[tab] ?? []) : [];

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">內容成效報告</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">過去 30 天各內容類型的流量與互動統計</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => load(tab)} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {/* Tabs */}
      <div className="mb-4 flex gap-2">
        {TABS.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === t.key ? "bg-primary text-primary-foreground" : "bg-muted hover:bg-muted/80 text-muted-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />{t.label}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Summary */}
      {cur && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          {[
            { label: "總事件數", val: cur.summary?.total_events ?? 0 },
            { label: "涵蓋內容", val: cur.summary?.total_pages ?? 0 },
            { label: "唯一訪客", val: cur.summary?.total_unique_visitors ?? 0 },
          ].map(s => (
            <Card key={s.label}>
              <CardContent className="pt-4 pb-4">
                <p className="text-sm text-muted-foreground">{s.label}</p>
                <p className="mt-1 text-3xl font-bold">{s.val}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            {TABS.find(t => t.key === tab)?.label}詳情（過去 30 天）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : rows.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">尚無流量資料</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">內容</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">瀏覽量</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">唯一訪客</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">總事件</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rows.map((r, i) => (
                  <tr key={i} className="hover:bg-muted/30">
                    <td className="px-4 py-2">
                      <p className="font-medium">{r.title ?? r.slug}</p>
                      <p className="text-xs text-muted-foreground font-mono">{r.slug}</p>
                    </td>
                    <td className="px-4 py-2 text-right">{r.views ?? 0}</td>
                    <td className="px-4 py-2 text-right">{r.unique_visitors ?? 0}</td>
                    <td className="px-4 py-2 text-right">{r.events ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
