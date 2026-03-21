"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Link2, CheckCircle2, XCircle, UploadCloud } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Matches the actual CrmSyncLog SQLModel
type SyncLog = {
  id: string;
  crm: string;            // "salesforce" | "hubspot"
  direction: string;      // "push" | "pull"
  entity_type: string;    // "contact" | "opportunity"
  local_id?: string;
  remote_id?: string;
  status: string;         // "success" | "error" | "skipped"
  error_message?: string;
  payload_summary?: string;
  synced_at: string;
};

const CRM_LABEL: Record<string, string> = {
  salesforce: "Salesforce",
  hubspot: "HubSpot",
};

const DIRECTION_LABEL: Record<string, string> = {
  push: "推送 →",
  pull: "← 拉取",
};

const STATUS_COLOR: Record<string, string> = {
  success: "bg-green-100 text-green-700",
  error:   "bg-red-100 text-red-700",
  skipped: "bg-gray-100 text-gray-600",
};

const STATUS_LABEL: Record<string, string> = {
  success: "成功",
  error:   "失敗",
  skipped: "略過",
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
  const [bulkSyncing, setBulkSyncing] = useState(false);
  const [bulkMsg, setBulkMsg] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/crm/sync-logs`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setLogs(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  async function bulkSync() {
    setBulkSyncing(true); setBulkMsg(null);
    try {
      const r = await fetch(`${API_BASE}/tracking/crm/sf/bulk-sync-contacts`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
      setBulkMsg("背景任務已啟動，同步完成後可重新整理查看記錄");
      setTimeout(() => { setBulkMsg(null); load(); }, 4000);
    } catch (e: unknown) {
      setBulkMsg(e instanceof Error ? e.message : "啟動失敗");
    } finally { setBulkSyncing(false); }
  }

  const counts = logs.reduce<Record<string, number>>((acc, l) => {
    const s = l.status ?? "error";
    acc[s] = (acc[s] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">CRM 整合</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            Salesforce 數據同步記錄與狀態監控
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <Button size="sm" onClick={bulkSync} disabled={bulkSyncing}>
            <UploadCloud className="mr-2 h-4 w-4" />
            {bulkSyncing ? "啟動中…" : "全部聯絡人同步至 Salesforce"}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {bulkMsg && (
        <Alert className="mb-4">
          <AlertDescription>{bulkMsg}</AlertDescription>
        </Alert>
      )}

      {/* Summary Cards — always visible */}
      <div className="mb-6 grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="flex items-center gap-3 pb-4 pt-4">
            <CheckCircle2 className="h-8 w-8 text-green-500" />
            <div>
              <p className="text-sm text-muted-foreground">成功</p>
              <p className="text-2xl font-bold">{counts.success ?? 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="flex items-center gap-3 pb-4 pt-4">
            <XCircle className="h-8 w-8 text-red-500" />
            <div>
              <p className="text-sm text-muted-foreground">失敗</p>
              <p className="text-2xl font-bold">{counts.error ?? 0}</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pb-4 pt-4">
            <p className="text-sm text-muted-foreground">略過</p>
            <p className="text-2xl font-bold">{counts.skipped ?? 0}</p>
          </CardContent>
        </Card>
      </div>

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
              <p className="mt-1 text-xs text-muted-foreground">
                設定 Salesforce 憑證後，點擊右上角「全部聯絡人同步」即可開始
              </p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">CRM</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">實體</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">方向</th>
                  <th className="px-4 py-2 text-center font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">摘要 / 錯誤</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">同步時間</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {logs.slice(0, 50).map(l => (
                  <tr key={l.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 text-muted-foreground">
                      {CRM_LABEL[l.crm] ?? l.crm}
                    </td>
                    <td className="px-4 py-2 font-medium">{l.entity_type}</td>
                    <td className="px-4 py-2 text-muted-foreground">
                      {DIRECTION_LABEL[l.direction] ?? l.direction}
                    </td>
                    <td className="px-4 py-2 text-center">
                      <Badge className={`text-xs ${STATUS_COLOR[l.status] ?? "bg-gray-100 text-gray-600"}`}>
                        {STATUS_LABEL[l.status] ?? l.status}
                      </Badge>
                    </td>
                    <td className="max-w-xs px-4 py-2 text-xs text-muted-foreground">
                      {l.status === "error" && l.error_message ? (
                        <span className="text-red-600">{l.error_message}</span>
                      ) : (
                        <span className="truncate">{l.payload_summary ?? "—"}</span>
                      )}
                    </td>
                    <td className="px-4 py-2 text-xs text-muted-foreground">{fmt(l.synced_at)}</td>
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
