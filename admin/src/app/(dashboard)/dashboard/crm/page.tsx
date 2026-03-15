"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Link2, CheckCircle2, XCircle, Clock } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type SyncLog = {
  id: string;
  direction?: string;
  entity_type?: string;
  entity_id?: string;
  status?: string;
  error_message?: string;
  records_synced?: number;
  synced_at?: string;
  created_at?: string;
};

const STATUS_COLOR: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  failed: "bg-red-100 text-red-700",
  pending: "bg-yellow-100 text-yellow-700",
  skipped: "bg-gray-100 text-gray-600",
};

function fmt(d?: string) {
  if (!d) return "—";
  return new Date(d).toLocaleString("zh-TW");
}

export default function CRMPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/crm/sync-logs`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setLogs(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const counts = logs.reduce<Record<string, number>>((acc, l) => {
    const s = l.status ?? "pending";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">CRM 整合</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">HubSpot CRM 數據同步記錄與狀態監控</p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {logs.length > 0 && (
        <div className="mb-6 grid grid-cols-4 gap-4">
          <Card><CardContent className="pt-4 pb-4 flex items-center gap-3">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <div><p className="text-sm text-muted-foreground">成功</p><p className="text-2xl font-bold">{counts.success ?? 0}</p></div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-4 flex items-center gap-3">
            <XCircle className="h-8 w-8 text-red-500" />
            <div><p className="text-sm text-muted-foreground">失敗</p><p className="text-2xl font-bold">{counts.failed ?? 0}</p></div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-4 flex items-center gap-3">
            <Clock className="h-8 w-8 text-yellow-500" />
            <div><p className="text-sm text-muted-foreground">等待中</p><p className="text-2xl font-bold">{counts.pending ?? 0}</p></div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">總同步筆數</p>
            <p className="text-2xl font-bold">{logs.reduce((s, l) => s + (l.records_synced ?? 0), 0)}</p>
          </CardContent></Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Link2 className="h-4 w-4 text-primary" />同步記錄（{logs.length}）
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">載入中…</p>
          ) : logs.length === 0 ? (
            <div className="py-16 text-center">
              <Link2 className="mx-auto mb-3 h-10 w-10 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground">尚無 CRM 同步記錄</p>
              <p className="mt-1 text-xs text-muted-foreground">設定 HubSpot API 金鑰後，聯絡人 / RFQ 資料將自動同步</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">實體類型</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">方向</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">筆數</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">同步時間</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.slice(0, 30).map(l => (
                  <tr key={l.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-medium">{l.entity_type ?? "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{l.direction ?? "push"}</td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={`text-xs ${STATUS_COLOR[l.status ?? "pending"] ?? ""}`}>{l.status ?? "pending"}</Badge>
                    </td>
                    <td className="px-4 py-2 text-right">{l.records_synced ?? 0}</td>
                    <td className="px-4 py-2 text-muted-foreground text-xs">{fmt(l.synced_at ?? l.created_at)}</td>
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
