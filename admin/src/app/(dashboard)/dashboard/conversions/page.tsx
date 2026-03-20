"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FileText, AlertCircle, UserCheck, UserX } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type RFQ = {
  id: string;
  rfq_number: string;
  contact_id?: string;
  visitor_id?: string;
  status: string;
  priority: string;
  intent_score_at_submit: number;
  assigned_to?: string;
  created_at: string;
};

// priority: "urgent" | "high" | "normal"
const PRIORITY_LABEL: Record<string, string> = {
  urgent: "緊急",
  high: "高",
  normal: "一般",
};
const PRIORITY_COLOR: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  normal: "bg-gray-100 text-gray-600",
};

// status: "new" | "reviewed" | "quoted" | "closed" | "rejected"
const STATUS_LABEL: Record<string, string> = {
  new: "未報價",
  reviewed: "審核中",
  quoted: "已報價",
  closed: "已結案",
  rejected: "已拒絕",
};
const STATUS_COLOR: Record<string, string> = {
  new: "bg-orange-100 text-orange-700",
  reviewed: "bg-yellow-100 text-yellow-700",
  quoted: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-600",
  rejected: "bg-red-100 text-red-700",
};

const PRIORITY_ORDER: Record<string, number> = { urgent: 0, high: 1, normal: 2 };

function fmt(d: string) {
  return new Date(d).toLocaleDateString("zh-TW", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export default function ConversionsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/rfqs`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : Promise.reject(new Error(`API ${r.status}`))))
      .then(d => setRfqs(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const unquoted = rfqs.filter(r => r.status === "new" || r.status === "reviewed");
  const quoted   = rfqs.filter(r => r.status === "quoted");
  const unassigned = rfqs.filter(r => !r.assigned_to);
  const assigned   = rfqs.filter(r => !!r.assigned_to);

  // Sorted table: urgent → high → normal, then newest first
  const sortedRfqs = [...rfqs].sort((a, b) => {
    const pd = (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9);
    return pd !== 0 ? pd : new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">詢價單管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">待處理詢價提醒與報價狀態追蹤</p>
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

      {/* Summary KPI Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">總 RFQ 數</p>
            <p className="mt-1 text-3xl font-bold">{rfqs.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">未報價</p>
            <p className={`mt-1 text-3xl font-bold ${unquoted.length > 0 ? "text-orange-600" : ""}`}>{unquoted.length}</p>
            <p className="text-xs text-muted-foreground">待處理</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">已報價</p>
            <p className="mt-1 text-3xl font-bold text-green-600">{quoted.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">未指派</p>
            <p className={`mt-1 text-3xl font-bold ${unassigned.length > 0 ? "text-red-600" : ""}`}>{unassigned.length}</p>
            <p className="text-xs text-muted-foreground">需指派負責人</p>
          </CardContent>
        </Card>
      </div>

      {/* Action Reminder Cards */}
      <div className="mb-6 grid gap-6 lg:grid-cols-2">
        {/* 未報價明細 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-4 w-4 text-orange-500" />
              未報價詢價單
              {unquoted.length > 0 && (
                <Badge className="ml-auto bg-orange-100 text-orange-700">{unquoted.length} 待處理</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {unquoted.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">✓ 無待處理詢價單</p>
            ) : (
              <div className="space-y-2">
                {unquoted
                  .sort((a, b) => (PRIORITY_ORDER[a.priority] ?? 9) - (PRIORITY_ORDER[b.priority] ?? 9))
                  .map(r => (
                    <div key={r.id} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                      <span className="font-mono font-medium">{r.rfq_number}</span>
                      <div className="flex items-center gap-2">
                        <Badge className={`text-xs ${PRIORITY_COLOR[r.priority] ?? ""}`}>
                          {PRIORITY_LABEL[r.priority] ?? r.priority}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{fmt(r.created_at)}</span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 指派狀況 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <UserX className="h-4 w-4 text-red-500" />
              指派狀況
              {unassigned.length > 0 && (
                <Badge className="ml-auto bg-red-100 text-red-700">{unassigned.length} 未指派</Badge>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="mb-3 flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
              <span className="flex items-center gap-1.5"><UserCheck className="h-3.5 w-3.5 text-green-600" />已指派</span>
              <span className="font-bold">{assigned.length}</span>
            </div>
            <div className="flex items-center justify-between rounded-md bg-muted/50 px-3 py-2 text-sm">
              <span className="flex items-center gap-1.5"><UserX className="h-3.5 w-3.5 text-red-500" />未指派</span>
              <span className={`font-bold ${unassigned.length > 0 ? "text-red-600" : ""}`}>{unassigned.length}</span>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* RFQ Table — sorted by priority then date */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-muted-foreground" />所有詢價紀錄
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {sortedRfqs.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">尚無 RFQ 資料</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">RFQ #</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">優先度</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">指派給</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {sortedRfqs.map(r => (
                  <tr key={r.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-mono font-medium">{r.rfq_number}</td>
                    <td className="px-4 py-2">
                      <Badge className={`text-xs ${STATUS_COLOR[r.status] ?? ""}`}>
                        {STATUS_LABEL[r.status] ?? r.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-2">
                      <Badge className={`text-xs ${PRIORITY_COLOR[r.priority] ?? ""}`}>
                        {PRIORITY_LABEL[r.priority] ?? r.priority}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 text-muted-foreground">{r.assigned_to ?? "—"}</td>
                    <td className="px-4 py-2 text-muted-foreground">{fmt(r.created_at)}</td>
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
