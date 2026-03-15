"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, FileText, TrendingUp, AlertCircle, CheckCircle2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

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

const STATUS_COLOR: Record<string, string> = {
  new: "bg-blue-100 text-blue-700",
  reviewed: "bg-yellow-100 text-yellow-700",
  quoted: "bg-green-100 text-green-700",
  closed: "bg-gray-100 text-gray-600",
  rejected: "bg-red-100 text-red-700",
};

const PRIORITY_COLOR: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-yellow-100 text-yellow-700",
  low: "bg-gray-100 text-gray-600",
};

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
    setLoading(true); setError(null);
    fetch(`${API_BASE}/tracking/rfqs`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json())
      .then(d => setRfqs(Array.isArray(d) ? d : d.items ?? []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const statusCounts = rfqs.reduce<Record<string, number>>((acc, r) => {
    acc[r.status] = (acc[r.status] ?? 0) + 1; return acc;
  }, {});
  const priorityCounts = rfqs.reduce<Record<string, number>>((acc, r) => {
    acc[r.priority] = (acc[r.priority] ?? 0) + 1; return acc;
  }, {});
  const avgScore = rfqs.length
    ? Math.round(rfqs.reduce((s, r) => s + (r.intent_score_at_submit ?? 0), 0) / rfqs.length)
    : 0;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">轉換分析</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">RFQ 詢價轉換率與狀態追蹤</p>
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

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">總 RFQ 數</p>
            <p className="mt-1 text-3xl font-bold">{rfqs.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">已報價</p>
            <p className="mt-1 text-3xl font-bold text-green-600">{statusCounts.quoted ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">高優先</p>
            <p className="mt-1 text-3xl font-bold text-red-600">{priorityCounts.high ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4 pb-4">
            <p className="text-sm text-muted-foreground">平均意圖分</p>
            <p className="mt-1 text-3xl font-bold">{avgScore}</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Status breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" />狀態分佈
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(statusCounts).length === 0
              ? <p className="text-sm text-muted-foreground">無資料</p>
              : Object.entries(statusCounts).map(([s, c]) => (
                <div key={s} className="flex items-center justify-between">
                  <Badge className={STATUS_COLOR[s] ?? ""}>{s}</Badge>
                  <span className="font-bold">{c}</span>
                </div>
              ))}
          </CardContent>
        </Card>

        {/* Priority breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <AlertCircle className="h-4 w-4 text-orange-500" />優先度分佈
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {Object.entries(priorityCounts).length === 0
              ? <p className="text-sm text-muted-foreground">無資料</p>
              : Object.entries(priorityCounts).map(([p, c]) => (
                <div key={p} className="flex items-center justify-between">
                  <Badge className={PRIORITY_COLOR[p] ?? ""}>{p}</Badge>
                  <span className="font-bold">{c}</span>
                </div>
              ))}
          </CardContent>
        </Card>

        {/* Assigned */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle2 className="h-4 w-4 text-green-500" />指派摘要
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">已指派</span>
                <span className="font-bold">{rfqs.filter(r => r.assigned_to).length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">未指派</span>
                <span className="font-bold">{rfqs.filter(r => !r.assigned_to).length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">有聯絡人</span>
                <span className="font-bold">{rfqs.filter(r => r.contact_id).length}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">訪客匿名</span>
                <span className="font-bold">{rfqs.filter(r => !r.contact_id && r.visitor_id).length}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* RFQ Table */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <FileText className="h-4 w-4 text-muted-foreground" />所有詢價紀錄
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {rfqs.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">尚無 RFQ 資料</p>
          ) : (
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">RFQ #</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">狀態</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">優先度</th>
                  <th className="px-4 py-2 text-right font-medium text-muted-foreground">意圖分</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">指派給</th>
                  <th className="px-4 py-2 text-left font-medium text-muted-foreground">建立時間</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {rfqs.map(r => (
                  <tr key={r.id} className="hover:bg-muted/30">
                    <td className="px-4 py-2 font-mono font-medium">{r.rfq_number}</td>
                    <td className="px-4 py-2">
                      <Badge className={`text-xs ${STATUS_COLOR[r.status] ?? ""}`}>{r.status}</Badge>
                    </td>
                    <td className="px-4 py-2">
                      <Badge className={`text-xs ${PRIORITY_COLOR[r.priority] ?? ""}`}>{r.priority}</Badge>
                    </td>
                    <td className="px-4 py-2 text-right font-bold">{r.intent_score_at_submit ?? 0}</td>
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
