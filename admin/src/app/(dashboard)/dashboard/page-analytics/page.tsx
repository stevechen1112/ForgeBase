"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, BarChart2 } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type PageRow = { slug: string; title?: string; views?: number; unique_visitors?: number; events?: number; avg_time_on_page?: number };
type Analytics = { period_days: number; summary: { total_events: number; total_pages: number; total_unique_visitors: number }; pages: PageRow[] };

const DAYS_OPTIONS = [7, 14, 30, 90];

export default function PageAnalyticsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [days, setDays] = useState(30);
  const [data, setData] = useState<Analytics | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/analytics/pages?days=${days}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setData).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token, days]);

  useEffect(() => { load(); }, [load]);

  const rows = data?.pages ?? [];
  const sorted = [...rows].sort((a, b) => (b.views ?? 0) - (a.views ?? 0));

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">頁面分析</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">各頁面流量、訪客與互動事件統計</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex rounded-md border overflow-hidden text-sm">
            {DAYS_OPTIONS.map(d => (
              <button
                key={d}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 ${days === d ? "bg-primary text-primary-foreground" : "hover:bg-muted/50"}`}
              >{d}天</button>
            ))}
          </div>
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {data && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">涵蓋頁面</p><p className="mt-1 text-3xl font-bold">{data.summary.total_pages}</p></CardContent></Card>
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">唯一訪客</p><p className="mt-1 text-3xl font-bold">{data.summary.total_unique_visitors}</p></CardContent></Card>
          <Card><CardContent className="pt-4 pb-4"><p className="text-sm text-muted-foreground">總事件數</p><p className="mt-1 text-3xl font-bold">{data.summary.total_events}</p></CardContent></Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <BarChart2 className="h-4 w-4 text-primary" />頁面流量詳情（過去 {days} 天）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : sorted.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">所選期間尚無流量資料</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">#</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">頁面</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">瀏覽量</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">唯一訪客</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">事件數</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sorted.map((r, i) => (
                  <tr key={i} className="hover:bg-muted/30">
                    <td className="px-4 py-2 text-muted-foreground">{i + 1}</td>
                    <td className="px-4 py-2">
                      <p className="font-medium">{r.title ?? r.slug}</p>
                      <p className="text-xs font-mono text-muted-foreground">/{r.slug}</p>
                    </td>
                    <td className="px-4 py-2 text-right font-bold">{r.views ?? 0}</td>
                    <td className="px-4 py-2 text-right">{r.unique_visitors ?? 0}</td>
                    <td className="px-4 py-2 text-right text-muted-foreground">{r.events ?? 0}</td>
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
