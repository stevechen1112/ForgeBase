"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Download, RefreshCw, Search } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { authApi, type TeamMember } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

type RFQ = {
  id: string;
  rfq_number: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  assigned_to_name: string | null;
  next_follow_up_at: string | null;
  source_page: string | null;
  created_at: string;
  sla_breached: boolean;
  is_spam: boolean;
  merged_into_rfq_id: string | null;
  contact: {
    full_name: string;
    company_name: string | null;
    email: string;
    country: string | null;
  } | null;
};

type RfqStats = {
  unquoted: number;
  unassigned: number;
  overdue_follow_ups: number;
  due_today: number;
};

const STATUS_LABEL: Record<string, string> = {
  new: "待處理",
  assigned: "待處理（已分派）",
  in_progress: "聯繫中",
  quoted: "報價／樣品",
  negotiation: "洽談中",
  won: "已成交",
  lost: "未成交",
  expired: "已結案",
};

const STATUS_STYLE: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-sky-100 text-sky-800",
  in_progress: "bg-amber-100 text-amber-800",
  quoted: "bg-violet-100 text-violet-800",
  negotiation: "bg-indigo-100 text-indigo-800",
  won: "bg-emerald-100 text-emerald-800",
  lost: "bg-muted text-muted-foreground",
  expired: "bg-slate-100 text-slate-700",
};

const SELECT_CLS = "h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";
const CLOSED = new Set(["won", "lost", "expired"]);

function formatDate(value: string | null, withTime = false) {
  if (!value) return "尚未設定";
  return new Date(value).toLocaleString("zh-TW", withTime
    ? { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { year: "numeric", month: "numeric", day: "numeric" });
}

type RFQsListPageProps = {
  mineOnly?: boolean;
};

export function RFQsListPage({ mineOnly = false }: RFQsListPageProps) {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const isManager = user?.role === "owner" || user?.role === "admin";

  const [rows, setRows] = useState<RFQ[]>([]);
  const [stats, setStats] = useState<RfqStats | null>(null);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [ownerFilter, setOwnerFilter] = useState("");
  const [followUpFilter, setFollowUpFilter] = useState("");
  const [view, setView] = useState("active");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;
  const assignedToFilter = mineOnly ? user?.id ?? "" : ownerFilter;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({
      limit: String(pageSize),
      offset: String((page - 1) * pageSize),
      view,
    });
    if (search.trim()) params.set("search", search.trim());
    if (statusFilter) params.set("status", statusFilter);
    if (assignedToFilter && isManager) params.set("assigned_to", assignedToFilter);
    if (followUpFilter === "response_overdue") params.set("sla", "breached");
    else if (followUpFilter) params.set("follow_up", followUpFilter);
    try {
      const response = await fetch(`${API_BASE}/tracking/rfqs?${params}`, { headers: buildApiHeaders(token) });
      const data = await response.json().catch(() => null);
      if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
      setRows(Array.isArray(data) ? data : []);
    } catch (cause) {
      setRows([]);
      setError(cause instanceof Error ? cause.message : "詢價案件載入失敗");
    } finally {
      setLoading(false);
    }
  }, [assignedToFilter, followUpFilter, isManager, page, search, statusFilter, token, view]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const linkedFollowUp = params.get("follow_up");
    const linkedSla = params.get("sla");
    if (linkedFollowUp && ["due", "overdue", "today", "upcoming"].includes(linkedFollowUp)) setFollowUpFilter(linkedFollowUp);
    if (linkedSla === "breached") setFollowUpFilter("response_overdue");
  }, []);

  useEffect(() => {
    if (!token) return;
    const params = new URLSearchParams({ days: "30" });
    if (mineOnly && isManager && user?.id) params.set("assigned_to", user.id);
    fetch(`${API_BASE}/tracking/rfqs/stats?${params}`, { headers: buildApiHeaders(token) })
      .then(async (response) => response.ok ? response.json() : null)
      .then(setStats)
      .catch(() => setStats(null));
    if (isManager) {
      authApi.listTeam(token)
        .then((members) => setTeam(members.filter((member) => member.is_active && ["sales", "admin", "owner"].includes(member.role))))
        .catch(() => setTeam([]));
    }
  }, [isManager, mineOnly, token, user?.id]);

  async function downloadCsv() {
    setExporting(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (mineOnly && user?.id) params.set("assigned_to", user.id);
      const response = await fetch(`${API_BASE}/tracking/rfqs/export.csv?${params}`, { headers: buildApiHeaders(token) });
      if (!response.ok) throw new Error("匯出失敗");
      const blob = await response.blob();
      const href = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = href;
      link.download = `forgebase-rfqs-${new Date().toISOString().slice(0, 10)}.csv`;
      link.click();
      URL.revokeObjectURL(href);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "匯出失敗");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{mineOnly ? "我的詢價案件" : "詢價案件"}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {mineOnly
              ? "只顯示分派給您的詢價與今天要跟進的案件。"
              : isManager
                ? "掌握新詢價、負責業務與下一步。"
                : "只顯示分派給您的詢價與今天要跟進的案件。"}
          </p>
        </div>
        {isManager && (
          <Button variant="outline" size="sm" onClick={downloadCsv} disabled={exporting}>
            <Download className="mr-2 h-4 w-4" />{exporting ? "匯出中…" : mineOnly ? "匯出我的案件" : "匯出 CSV"}
          </Button>
        )}
      </div>

      {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className={`mb-5 grid gap-3 ${isManager && !mineOnly ? "sm:grid-cols-4" : "sm:grid-cols-3"}`}>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">待處理案件</p><p className="mt-1 text-2xl font-bold">{stats?.unquoted ?? "—"}</p></CardContent></Card>
        {isManager && !mineOnly && <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">尚未分派</p><p className={`mt-1 text-2xl font-bold ${(stats?.unassigned ?? 0) > 0 ? "text-red-600" : ""}`}>{stats?.unassigned ?? "—"}</p></CardContent></Card>}
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">24 小時內要跟進</p><p className="mt-1 text-2xl font-bold">{stats?.due_today ?? "—"}</p></CardContent></Card>
        <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">跟進已逾期</p><p className={`mt-1 text-2xl font-bold ${(stats?.overdue_follow_ups ?? 0) > 0 ? "text-red-600" : ""}`}>{stats?.overdue_follow_ups ?? "—"}</p></CardContent></Card>
      </div>

      <div className="mb-4 flex flex-wrap gap-2">
        <div className="relative min-w-56 flex-1">
          <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
          <Input className="pl-9" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="搜尋公司、姓名、Email 或案件編號" />
        </div>
        <select className={SELECT_CLS} aria-label="案件階段" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}>
          <option value="">全部階段</option>
          {Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        {isManager && !mineOnly && (
          <select className={SELECT_CLS} aria-label="負責業務" value={ownerFilter} onChange={(event) => { setOwnerFilter(event.target.value); setPage(1); }}>
            <option value="">全部負責人</option>
            {team.map((member) => <option key={member.id} value={member.id}>{member.full_name}</option>)}
          </select>
        )}
        <select className={SELECT_CLS} aria-label="跟進期限" value={followUpFilter} onChange={(event) => { setFollowUpFilter(event.target.value); setPage(1); }}>
          <option value="">全部跟進期限</option>
          <option value="due">已到期或 24 小時內</option>
          <option value="overdue">已逾期</option>
          <option value="today">24 小時內</option>
          <option value="upcoming">即將到期</option>
          <option value="response_overdue">尚未回覆且已逾期</option>
        </select>
        <select className={SELECT_CLS} aria-label="案件資料夾" value={view} onChange={(event) => { setView(event.target.value); setPage(1); }}>
          <option value="active">一般案件</option>
          <option value="spam">垃圾隔離區</option>
          {isManager && <option value="merged">已合併案件</option>}
        </select>
        <Button variant="outline" size="sm" className="h-10" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      <div className="overflow-x-auto rounded-lg border bg-card">
        {loading ? (
          <div className="py-14 text-center text-sm text-muted-foreground">載入詢價案件…</div>
        ) : rows.length === 0 ? (
          <div className="py-14 text-center text-sm text-muted-foreground">目前沒有符合條件的詢價案件</div>
        ) : (
          <table className="w-full min-w-[920px] text-sm">
            <thead className="border-b bg-muted/50">
              <tr>{["買家與公司", "需求案件", "階段", "負責業務", "下一步", "收到時間", ""].map((heading) => <th key={heading} className="px-4 py-3 text-left font-medium text-muted-foreground">{heading}</th>)}</tr>
            </thead>
            <tbody className="divide-y">
              {rows.map((rfq) => {
                const overdue = Boolean(rfq.next_follow_up_at && new Date(rfq.next_follow_up_at) < new Date() && !CLOSED.has(rfq.status));
                return (
                  <tr key={rfq.id} className={overdue || rfq.sla_breached ? "bg-red-50/50" : "hover:bg-muted/30"}>
                    <td className="px-4 py-3">
                      <p className="font-medium">{rfq.contact?.company_name || "未填公司"}</p>
                      <p className="text-xs text-muted-foreground">{rfq.contact?.full_name || "未填姓名"}{rfq.contact?.country ? ` · ${rfq.contact.country}` : ""}</p>
                    </td>
                    <td className="px-4 py-3"><Link href={`/dashboard/rfqs/${rfq.id}`} className="font-mono text-xs font-semibold text-primary hover:underline">{rfq.rfq_number}</Link>{rfq.priority === "urgent" && <span className="ml-2 text-xs font-semibold text-red-600">緊急</span>}</td>
                    <td className="px-4 py-3"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLE[rfq.status] ?? "bg-muted"}`}>{STATUS_LABEL[rfq.status] ?? rfq.status}</span></td>
                    <td className="px-4 py-3">{rfq.assigned_to_name || <span className="text-red-600">尚未分派</span>}</td>
                    <td className="px-4 py-3"><p className={overdue ? "font-semibold text-red-600" : ""}>{formatDate(rfq.next_follow_up_at, true)}</p>{overdue && <p className="text-xs text-red-600">已逾期</p>}</td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDate(rfq.created_at)}</td>
                    <td className="px-4 py-3"><Button asChild variant="ghost" size="sm"><Link href={`/dashboard/rfqs/${rfq.id}`}>處理案件 →</Link></Button></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground">
        <span>第 {page} 頁 · 本頁 {rows.length} 件</span>
        <div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一頁</Button><Button variant="outline" size="sm" disabled={rows.length < pageSize} onClick={() => setPage((value) => value + 1)}>下一頁</Button></div>
      </div>
    </div>
  );
}

export default function RFQsPage() {
  return <RFQsListPage />;
}
