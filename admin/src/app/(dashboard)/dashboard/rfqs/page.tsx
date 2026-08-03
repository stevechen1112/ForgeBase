"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { QualityBadge, SlaCountdown } from "@/components/rfq/quality-sla";

type RFQ = {
  id: string;
  rfq_number: string;
  contact_id: string | null;
  status: string;
  priority: string;
  intent_score_at_submit: number;
  quality_score: number;
  sla_due_at: string | null;
  sla_breached: boolean;
  assigned_to: string | null;
  created_at: string;
};

type RfqStats = {
  total_rfqs: number;
  avg_first_response_hours: number | null;
  sla_achievement_rate: number | null;
  sla_breached: number;
  avg_quality_score: number | null;
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
  const [stats, setStats] = useState<RfqStats | null>(null);
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [slaFilter, setSlaFilter] = useState("");
  const [sort, setSort] = useState("quality"); // T11：預設「品質 × SLA」
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
    if (slaFilter) params.set("sla", slaFilter);
    if (sort) params.set("sort", sort);

    fetch(`${API_BASE}/tracking/rfqs?${params}`, {
      headers: buildApiHeaders(token),
    })
      .then((r) => r.json())
      .then((data) => setRows(Array.isArray(data) ? data : []))
      .catch((e) => { setError(e instanceof Error ? e.message : "Load failed"); setRows([]); })
      .finally(() => setLoading(false));
  }, [token, page, statusFilter, priorityFilter, slaFilter, sort]);

  // T8：首回時間與 SLA 達成率摘要
  useEffect(() => {
    fetch(`${API_BASE}/tracking/rfqs/stats?days=30`, { headers: buildApiHeaders(token) })
      .then((r) => r.json())
      .then((data) => setStats(data && typeof data === "object" ? data : null))
      .catch(() => setStats(null));
  }, [token]);

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

      {/* T8：首回速度摘要卡（近 30 天） */}
      {stats && (
        <div className="mb-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <div className="rounded-lg border bg-card p-3">
            <div className="text-xs text-muted-foreground">平均首回時間</div>
            <div className="mt-1 text-xl font-bold">
              {stats.avg_first_response_hours != null ? `${stats.avg_first_response_hours}h` : "—"}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <div className="text-xs text-muted-foreground">SLA 達成率</div>
            <div className={`mt-1 text-xl font-bold ${stats.sla_achievement_rate != null && stats.sla_achievement_rate < 0.8 ? "text-red-600" : ""}`}>
              {stats.sla_achievement_rate != null ? `${Math.round(stats.sla_achievement_rate * 100)}%` : "—"}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <div className="text-xs text-muted-foreground">SLA 逾期單</div>
            <div className={`mt-1 text-xl font-bold ${stats.sla_breached > 0 ? "text-red-600" : ""}`}>
              {stats.sla_breached}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-3">
            <div className="text-xs text-muted-foreground">平均品質分</div>
            <div className="mt-1 text-xl font-bold">
              {stats.avg_quality_score != null ? stats.avg_quality_score : "—"}
            </div>
          </div>
        </div>
      )}

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
        <select className={SELECT_CLS} value={slaFilter} onChange={(e) => { setSlaFilter(e.target.value); setPage(1); }}>
          <option value="">All SLA</option>
          <option value="due_soon">SLA 即將逾期</option>
          <option value="breached">SLA 已逾期</option>
        </select>
        <select className={SELECT_CLS} value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
          <option value="quality">品質 × SLA（預設）</option>
          <option value="">最新優先</option>
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
                {["RFQ #", "Status", "Priority", "Quality", "SLA", "Intent", "Submitted", "Actions"].map((h) => (
                  <th key={h} className="px-4 py-3 text-left font-medium text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((rfq) => (
                <tr key={rfq.id} className={`hover:bg-muted/30 transition-colors ${rfq.sla_breached ? "bg-red-50/50" : ""}`}>
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
                  <td className="px-4 py-3"><QualityBadge score={rfq.quality_score ?? 0} /></td>
                  <td className="px-4 py-3">
                    <SlaCountdown slaDueAt={rfq.sla_due_at} slaBreached={rfq.sla_breached} status={rfq.status} />
                  </td>
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
