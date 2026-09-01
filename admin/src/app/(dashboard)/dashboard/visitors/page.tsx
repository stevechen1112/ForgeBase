"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Eye, RefreshCw, Users } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";

type Visitor = {
  visitor_id: string;
  total_visits: number;
  total_page_views: number;
  device_type?: string | null;
  country?: string | null;
  contact_id?: string | null;
  first_seen: string;
  last_seen: string;
  last_activity_at: string;
};

function dateTime(value: string) {
  return new Date(value).toLocaleString("zh-TW");
}

export default function VisitorsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [visitors, setVisitors] = useState<Visitor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE}/tracking/visitors?limit=200&sort=last_activity`, {
        headers: buildApiHeaders(token),
      });
      if (!response.ok) throw new Error("無法讀取訪客活動");
      setVisitors(await response.json());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "讀取失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  const totals = useMemo(() => ({
    visits: visitors.reduce((sum, row) => sum + row.total_visits, 0),
    views: visitors.reduce((sum, row) => sum + row.total_page_views, 0),
    known: visitors.filter((row) => row.contact_id).length,
  }), [visitors]);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">網站訪客活動</h1>
          <p className="text-sm text-muted-foreground">只呈現實際造訪、瀏覽與已連結聯絡人，不推測買家分數。</p>
        </div>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="grid gap-4 sm:grid-cols-3">
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Users className="h-4 w-4" />訪客</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{visitors.length}</CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Activity className="h-4 w-4" />總造訪</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{totals.visits}</CardContent></Card>
        <Card><CardHeader><CardTitle className="flex items-center gap-2 text-sm"><Eye className="h-4 w-4" />總瀏覽</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{totals.views}</CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle className="text-base">最近活動</CardTitle></CardHeader>
        <CardContent className="overflow-x-auto p-0">
          <table className="w-full text-sm">
            <thead className="border-y bg-muted/40 text-left"><tr><th className="px-4 py-3">訪客</th><th className="px-4 py-3">造訪／瀏覽</th><th className="px-4 py-3">國家／裝置</th><th className="px-4 py-3">最後活動</th></tr></thead>
            <tbody>
              {visitors.map((visitor, index) => (
                <tr key={visitor.visitor_id} className="border-b hover:bg-muted/30">
                  <td className="px-4 py-3"><Link className="font-medium text-primary hover:underline" href={`/dashboard/visitors/${visitor.visitor_id}`}>匿名訪客 #{index + 1}</Link>{visitor.contact_id && <span className="ml-2 text-xs text-emerald-700">已提供聯絡資料</span>}</td>
                  <td className="px-4 py-3">{visitor.total_visits}／{visitor.total_page_views}</td>
                  <td className="px-4 py-3">{visitor.country || "—"}／{visitor.device_type || "—"}</td>
                  <td className="px-4 py-3 text-muted-foreground">{dateTime(visitor.last_activity_at || visitor.last_seen)}</td>
                </tr>
              ))}
              {!loading && visitors.length === 0 && <tr><td className="px-4 py-8 text-center text-muted-foreground" colSpan={4}>尚無已同意追蹤的訪客活動</td></tr>}
            </tbody>
          </table>
        </CardContent>
      </Card>
    </div>
  );
}
