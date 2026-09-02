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
  status: "new" | "assigned" | "accepted" | "archived";
  priority: string;
  assigned_to: string | null;
  assigned_to_name: string | null;
  acceptance_due_at: string | null;
  acceptance_sla_breached: boolean;
  acknowledgement_sent_at: string | null;
  accepted_at: string | null;
  first_verified_response_at: string | null;
  archived_at: string | null;
  created_at: string;
  is_spam: boolean;
  merged_into_rfq_id: string | null;
  contact: { full_name: string; company_name: string | null; email: string; country: string | null } | null;
};

type RfqStats = {
  open: number;
  unassigned: number;
  awaiting_acceptance: number;
  overdue_acceptance: number;
  accepted: number;
  acknowledged: number;
  verified_responses: number;
};

const STATUS_LABEL: Record<RFQ["status"], string> = {
  new: "新進詢價",
  assigned: "已分派・待接手",
  accepted: "業務已接手",
  archived: "已封存",
};
const STATUS_STYLE: Record<RFQ["status"], string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-amber-100 text-amber-800",
  accepted: "bg-emerald-100 text-emerald-800",
  archived: "bg-slate-100 text-slate-700",
};
const SELECT_CLS = "h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

function formatDate(value: string | null, withTime = false) {
  if (!value) return "—";
  return new Date(value).toLocaleString("zh-TW", withTime
    ? { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }
    : { year: "numeric", month: "numeric", day: "numeric" });
}

function acceptanceText(rfq: RFQ) {
  if (rfq.status === "accepted") return `已接手 ${formatDate(rfq.accepted_at, true)}`;
  if (rfq.status === "archived") return `封存 ${formatDate(rfq.archived_at, true)}`;
  if (!rfq.assigned_to) return "等待主管分派";
  return `${rfq.acceptance_sla_breached ? "接手已逾期" : "接手期限"} ${formatDate(rfq.acceptance_due_at, true)}`;
}

export default function RFQsPage() {
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
  const [attentionFilter, setAttentionFilter] = useState("");
  const [view, setView] = useState("active");
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const params = new URLSearchParams({ limit: String(pageSize), offset: String((page - 1) * pageSize), view });
    if (search.trim()) params.set("search", search.trim());
    if (statusFilter) params.set("status", statusFilter);
    if (ownerFilter && isManager) params.set("assigned_to", ownerFilter);
    if (attentionFilter) params.set("attention", attentionFilter);
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
  }, [attentionFilter, isManager, ownerFilter, page, search, statusFilter, token, view]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const linkedAttention = new URLSearchParams(window.location.search).get("attention");
    if (linkedAttention && ["unassigned", "awaiting_acceptance", "acceptance_overdue"].includes(linkedAttention)) setAttentionFilter(linkedAttention);
  }, []);
  useEffect(() => {
    if (!token) return;
    fetch(`${API_BASE}/tracking/rfqs/stats?days=30`, { headers: buildApiHeaders(token) })
      .then(async (response) => response.ok ? response.json() : null).then(setStats).catch(() => setStats(null));
    if (isManager) authApi.listTeam(token)
      .then((members) => setTeam(members.filter((member) => member.is_active && ["sales", "admin", "owner"].includes(member.role))))
      .catch(() => setTeam([]));
  }, [isManager, token]);

  async function downloadCsv() {
    setExporting(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.set("status", statusFilter);
      if (ownerFilter) params.set("assigned_to", ownerFilter);
      const response = await fetch(`${API_BASE}/tracking/rfqs/export.csv?${params}`, { headers: buildApiHeaders(token) });
      if (!response.ok) throw new Error("匯出失敗");
      const href = URL.createObjectURL(await response.blob());
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

  return <div>
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div><h1 className="text-2xl font-bold tracking-tight">詢價承接</h1><p className="mt-1 text-sm text-muted-foreground">網站收到詢價後，在這裡完成確認、分派與業務接手；業務帳號只會看到分派給自己的案件。</p></div>
      {isManager && <Button variant="outline" size="sm" onClick={downloadCsv} disabled={exporting}><Download className="mr-2 h-4 w-4" />{exporting ? "匯出中…" : "匯出 CSV"}</Button>}
    </div>
    {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
    <div className="mb-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">目前待承接</p><p className="mt-1 text-2xl font-bold">{stats?.open ?? "—"}</p></CardContent></Card>
      <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">{isManager ? "尚未分派" : "等待我接手"}</p><p className={`mt-1 text-2xl font-bold ${isManager && (stats?.unassigned ?? 0) > 0 ? "text-red-600" : ""}`}>{isManager ? stats?.unassigned ?? "—" : stats?.awaiting_acceptance ?? "—"}</p></CardContent></Card>
      <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">已分派、等待接手</p><p className="mt-1 text-2xl font-bold">{stats?.awaiting_acceptance ?? "—"}</p></CardContent></Card>
      <Card><CardContent className="p-4"><p className="text-xs text-muted-foreground">接手已逾期</p><p className={`mt-1 text-2xl font-bold ${(stats?.overdue_acceptance ?? 0) > 0 ? "text-red-600" : ""}`}>{stats?.overdue_acceptance ?? "—"}</p></CardContent></Card>
    </div>
    <div className="mb-4 flex flex-wrap gap-2">
      <div className="relative min-w-56 flex-1"><Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" /><Input className="pl-9" value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} placeholder="搜尋公司、姓名、Email 或案件編號" /></div>
      <select className={SELECT_CLS} aria-label="承接狀態" value={statusFilter} onChange={(event) => { setStatusFilter(event.target.value); setPage(1); }}><option value="">全部承接狀態</option>{Object.entries(STATUS_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
      {isManager && <select className={SELECT_CLS} aria-label="負責業務" value={ownerFilter} onChange={(event) => { setOwnerFilter(event.target.value); setPage(1); }}><option value="">全部負責人</option>{team.map((member) => <option key={member.id} value={member.id}>{member.full_name}</option>)}</select>}
      <select className={SELECT_CLS} aria-label="需要注意" value={attentionFilter} onChange={(event) => { setAttentionFilter(event.target.value); setPage(1); }}><option value="">全部案件</option>{isManager && <option value="unassigned">尚未分派</option>}<option value="awaiting_acceptance">等待接手</option><option value="acceptance_overdue">接手已逾期</option></select>
      <select className={SELECT_CLS} aria-label="案件資料夾" value={view} onChange={(event) => { setView(event.target.value); setPage(1); }}><option value="active">有效詢價</option><option value="spam">垃圾隔離區</option>{isManager && <option value="merged">已合併案件</option>}</select>
      <Button variant="outline" size="sm" className="h-10" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
    </div>
    <div className="overflow-x-auto rounded-lg border bg-card">
      {loading ? <div className="py-14 text-center text-sm text-muted-foreground">載入詢價案件…</div> : rows.length === 0 ? <div className="py-14 text-center text-sm text-muted-foreground">目前沒有符合條件的詢價案件</div> : <table className="w-full min-w-[940px] text-sm">
        <thead className="border-b bg-muted/50"><tr>{["買家與公司", "詢價案件", "承接狀態", "負責業務", "接手期限", "收到時間", ""].map((heading) => <th key={heading} className="px-4 py-3 text-left font-medium text-muted-foreground">{heading}</th>)}</tr></thead>
        <tbody className="divide-y">{rows.map((rfq) => <tr key={rfq.id} className={rfq.acceptance_sla_breached ? "bg-red-50/60" : "hover:bg-muted/30"}>
          <td className="px-4 py-3"><p className="font-medium">{rfq.contact?.company_name || "未填公司"}</p><p className="text-xs text-muted-foreground">{rfq.contact?.full_name || "未填姓名"}{rfq.contact?.country ? ` · ${rfq.contact.country}` : ""}</p></td>
          <td className="px-4 py-3"><Link href={`/dashboard/rfqs/${rfq.id}`} className="font-mono text-xs font-semibold text-primary hover:underline">{rfq.rfq_number}</Link>{rfq.priority === "urgent" && <span className="ml-2 text-xs font-semibold text-red-600">緊急</span>}</td>
          <td className="px-4 py-3"><span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_STYLE[rfq.status]}`}>{STATUS_LABEL[rfq.status]}</span></td>
          <td className="px-4 py-3">{rfq.assigned_to_name || <span className="text-red-600">尚未分派</span>}</td>
          <td className={`px-4 py-3 ${rfq.acceptance_sla_breached ? "font-semibold text-red-600" : ""}`}>{acceptanceText(rfq)}{rfq.acknowledgement_sent_at && <p className="mt-1 text-xs font-normal text-muted-foreground">已寄收件確認</p>}</td>
          <td className="px-4 py-3 text-muted-foreground">{formatDate(rfq.created_at)}</td>
          <td className="px-4 py-3"><Button asChild variant="ghost" size="sm"><Link href={`/dashboard/rfqs/${rfq.id}`}>查看與承接 →</Link></Button></td>
        </tr>)}</tbody>
      </table>}
    </div>
    <div className="mt-4 flex items-center justify-between text-sm text-muted-foreground"><span>第 {page} 頁 · 本頁 {rows.length} 件</span><div className="flex gap-2"><Button variant="outline" size="sm" disabled={page === 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>上一頁</Button><Button variant="outline" size="sm" disabled={rows.length < pageSize} onClick={() => setPage((value) => value + 1)}>下一頁</Button></div></div>
  </div>;
}
