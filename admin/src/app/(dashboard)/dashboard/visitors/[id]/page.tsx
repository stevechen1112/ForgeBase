"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";

type Journey = {
  visitor: {
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
  summary: { total_events: number; total_chats: number; total_rfqs: number; event_breakdown: Record<string, number> };
  timeline: Array<Record<string, unknown> & { type: string; timestamp: string }>;
};

function dateTime(value: string) { return new Date(value).toLocaleString("zh-TW"); }

export default function VisitorDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<Journey | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/tracking/visitors/${id}/journey`, { headers: buildApiHeaders(token) });
      if (!response.ok) throw new Error("找不到訪客資料");
      setData(await response.json());
      setError(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "讀取失敗");
    } finally { setLoading(false); }
  }, [id, token]);

  useEffect(() => { void load(); }, [load]);

  if (loading) return <p className="py-10 text-center text-muted-foreground">載入中…</p>;
  if (error) return <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>;
  if (!data) return null;

  const visitor = data.visitor;
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div><h1 className="text-2xl font-bold">訪客活動明細</h1><p className="font-mono text-xs text-muted-foreground">{visitor.visitor_id}</p></div>
        <Button variant="outline" onClick={() => void load()}>重新整理</Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-4">
        <Card><CardHeader><CardTitle className="text-sm">造訪次數</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{visitor.total_visits}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">頁面瀏覽</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{visitor.total_page_views}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">聊天</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{data.summary.total_chats}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm">詢價</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{data.summary.total_rfqs}</CardContent></Card>
      </div>

      <Card><CardHeader><CardTitle className="text-base">基本活動資訊</CardTitle></CardHeader><CardContent className="grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4"><div><span className="text-muted-foreground">首次：</span>{dateTime(visitor.first_seen)}</div><div><span className="text-muted-foreground">最後：</span>{dateTime(visitor.last_activity_at || visitor.last_seen)}</div><div><span className="text-muted-foreground">國家：</span>{visitor.country || "—"}</div><div><span className="text-muted-foreground">裝置：</span>{visitor.device_type || "—"}</div></CardContent></Card>

      <Card>
        <CardHeader><CardTitle className="text-base">時間軸</CardTitle></CardHeader>
        <CardContent className="space-y-3">
          {data.timeline.map((entry, index) => (
            <div key={`${entry.type}-${entry.timestamp}-${index}`} className="flex gap-3 rounded-lg border p-3">
              <Badge variant="outline" className="h-fit">{entry.type === "event" ? "網站" : entry.type === "chat" ? "聊天" : "詢價"}</Badge>
              <div className="min-w-0"><p className="font-medium">{String(entry.event_name || entry.rfq_number || entry.status || "活動")}</p><p className="truncate text-xs text-muted-foreground">{String(entry.page_url || entry.company_name || "")} · {dateTime(entry.timestamp)}</p></div>
            </div>
          ))}
          {data.timeline.length === 0 && <p className="text-sm text-muted-foreground">尚無活動紀錄</p>}
        </CardContent>
      </Card>
    </div>
  );
}
