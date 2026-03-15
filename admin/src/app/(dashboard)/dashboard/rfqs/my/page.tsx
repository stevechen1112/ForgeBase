"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { API_BASE } from "@/lib/api/client";

type RFQ = {
  id: string;
  rfq_number: string;
  contact_id: string | null;
  status: string;
  priority: string;
  intent_score_at_submit: number;
  assigned_to: string | null;
  created_at: string;
};

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-yellow-100 text-yellow-800",
  in_progress: "bg-orange-100 text-orange-800",
  quoted: "bg-purple-100 text-purple-800",
  won: "bg-green-100 text-green-800",
  lost: "bg-muted text-muted-foreground",
  expired: "bg-red-100 text-red-700",
};

const PRIORITY_COLORS: Record<string, string> = {
  normal: "text-muted-foreground",
  high: "text-orange-600 font-semibold",
  urgent: "text-red-600 font-bold",
};

const SELECT_CLS = "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

export default function MyRFQsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const userId = state.status === "authenticated" ? state.user.id : "";

  const [rows, setRows] = useState<RFQ[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  const load = useCallback(() => {
    if (!userId) return;
    setLoading(true);
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String((page - 1) * PAGE_SIZE),
      assigned_to: userId,
    });
    if (statusFilter) params.set("status", statusFilter);
    fetch(`${API_BASE}/tracking/rfqs?${params}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => console.error("load my rfqs error", e))
      .finally(() => setLoading(false));
  }, [token, userId, statusFilter, page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">我的 RFQ</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">顯示指派給您的詢價單</p>
        </div>
        <Button asChild variant="outline" size="sm">
          <Link href="/dashboard/rfqs">查看全部 RFQ</Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select className={SELECT_CLS} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">全部狀態</option>
          <option value="new">新建</option>
          <option value="assigned">已指派</option>
          <option value="in_progress">處理中</option>
          <option value="quoted">已報價</option>
          <option value="won">成交</option>
          <option value="lost">未成交</option>
          <option value="expired">已過期</option>
        </select>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />重新整理
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 border-b">
            <tr>
              {["RFQ 編號", "狀態", "優先級", "意圖分數", "日期", "操作"].map((h) => (
                <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {loading && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">載入中…</td></tr>
            )}
            {!loading && rows.length === 0 && (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-muted-foreground">目前無指派給您的 RFQ</td></tr>
            )}
            {rows.map((rfq) => (
              <tr key={rfq.id} className="hover:bg-muted/30 transition-colors">
                <td className="px-4 py-3 font-mono text-xs">{rfq.rfq_number}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_COLORS[rfq.status] ?? "bg-muted text-muted-foreground"}`}>
                    {rfq.status}
                  </span>
                </td>
                <td className={`px-4 py-3 text-xs ${PRIORITY_COLORS[rfq.priority] ?? "text-muted-foreground"}`}>
                  {rfq.priority}
                </td>
                <td className="px-4 py-3">{rfq.intent_score_at_submit}</td>
                <td className="px-4 py-3 text-muted-foreground text-xs">
                  {new Date(rfq.created_at).toLocaleDateString("zh-TW")}
                </td>
                <td className="px-4 py-3">
                  <Button asChild variant="ghost" size="sm">
                    <Link href={`/dashboard/rfqs/${rfq.id}`}>查看詳情</Link>
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>第 {page} 頁</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>上一頁</Button>
          <Button variant="outline" size="sm" disabled={rows.length < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}>下一頁</Button>
        </div>
      </div>
    </div>
  );
}
