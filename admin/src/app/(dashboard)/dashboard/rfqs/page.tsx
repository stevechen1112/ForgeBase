"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

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

const STATUS_VARIANT: Record<string, string> = {
  new: "bg-blue-100 text-blue-800 hover:bg-blue-100",
  assigned: "bg-yellow-100 text-yellow-800 hover:bg-yellow-100",
  in_progress: "bg-orange-100 text-orange-800 hover:bg-orange-100",
  quoted: "bg-purple-100 text-purple-800 hover:bg-purple-100",
  won: "bg-green-100 text-green-800 hover:bg-green-100",
  lost: "bg-muted text-muted-foreground hover:bg-muted",
  expired: "bg-red-100 text-red-700 hover:bg-red-100",
};

const PRIORITY_CLS: Record<string, string> = {
  normal: "text-muted-foreground",
  high: "text-orange-600 font-semibold",
  urgent: "text-red-600 font-bold",
};

const SELECT_CLS = "rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring text-foreground";

export default function RFQsListPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [rows, setRows] = useState<RFQ[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 25;

  const load = useCallback(() => {
    setLoading(true); setError(null);
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: String((page - 1) * PAGE_SIZE),
    });
    if (statusFilter) params.set("status", statusFilter);
    if (priorityFilter) params.set("priority", priorityFilter);

    fetch(`${API_BASE}/tracking/rfqs?${params}`, {
      headers: buildApiHeaders(token),
    })
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => { setError(e instanceof Error ? e.message : "Load failed"); setRows([]); })
      .finally(() => setLoading(false));
  }, [token, page, statusFilter, priorityFilter]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">RFQ Requests</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">管理所有入站詢價單，依狀態、負責業務篩選並追蹤跟進進度</p>
        </div>
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      {/* Filters */}
      <div className="mb-4 flex flex-wrap gap-3">
        <select className={SELECT_CLS} value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          {["new", "assigned", "in_progress", "quoted", "won", "lost", "expired"].map((s) => (
            <option key={s} value={s}>{s.replace("_", " ")}</option>
          ))}
        </select>
        <select className={SELECT_CLS} value={priorityFilter} onChange={(e) => { setPriorityFilter(e.target.value); setPage(1); }}>
          <option value="">All Priorities</option>
          {["normal", "high", "urgent"].map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
        <Button variant="outline" size="sm" onClick={load} className="ml-auto">
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />Refresh
        </Button>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-hidden">
        {loading ? (
          <div className="py-12 text-center text-sm text-muted-foreground">載入中…</div>
        ) : rows.length === 0 ? (
          <div className="py-12 text-center text-sm text-muted-foreground">No RFQs found</div>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-muted/50 border-b">
              <tr>
                {["RFQ #", "Status", "Priority", "Intent Score", "Submitted", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((rfq) => (
                <tr key={rfq.id} className="hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3 font-mono font-medium text-primary">
                    <Link href={`/dashboard/rfqs/${rfq.id}`} className="hover:underline">
                      {rfq.rfq_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${STATUS_VARIANT[rfq.status] ?? "bg-muted text-muted-foreground"}`}>
                      {rfq.status.replace("_", " ")}
                    </span>
                  </td>
                  <td className={`px-4 py-3 ${PRIORITY_CLS[rfq.priority] ?? ""}`}>{rfq.priority}</td>
                  <td className="px-4 py-3">{rfq.intent_score_at_submit}</td>
                  <td className="px-4 py-3 text-muted-foreground">
                    {new Date(rfq.created_at).toLocaleDateString()}
                  </td>
                  <td className="px-4 py-3">
                    <Button asChild variant="ghost" size="sm">
                      <Link href={`/dashboard/rfqs/${rfq.id}`}>View →</Link>
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>{rows.length} results</span>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
          <Button variant="outline" size="sm" disabled={rows.length < PAGE_SIZE} onClick={() => setPage((p) => p + 1)}>Next</Button>
        </div>
      </div>
    </div>
  );
}
