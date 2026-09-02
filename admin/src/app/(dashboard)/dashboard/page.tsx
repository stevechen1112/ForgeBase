"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, ClipboardList, MailCheck, RefreshCw, UserRoundCheck } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";

type Stats = { total: number; open: number; unassigned: number; awaiting_acceptance: number; overdue_acceptance: number; accepted: number; archived: number; acknowledged: number; verified_responses: number; status_counts: Record<string, number> };
type RFQ = { id: string; rfq_number: string; status: string; priority: string; assigned_to_name: string | null; acceptance_due_at: string | null; acceptance_sla_breached: boolean; created_at: string; contact: { full_name: string; company_name: string | null; country: string | null } | null };
type TaskQueue = { total_open: number; tasks: { type: string; title: string; count: number }[] };

const STATUS_LABEL: Record<string, string> = { new: "新進詢價", assigned: "已分派", accepted: "已接手", archived: "已封存" };
function dateTime(value: string | null) { return value ? new Date(value).toLocaleString("zh-TW", { month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"; }

export default function DashboardPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const [stats, setStats] = useState<Stats | null>(null);
  const [rfqs, setRfqs] = useState<RFQ[]>([]);
  const [queue, setQueue] = useState<TaskQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      const [statsData, rfqData, queueData] = await Promise.all([
        apiClient.get<Stats>("/tracking/rfqs/stats?days=30", token),
        apiClient.get<RFQ[]>("/tracking/rfqs?view=active&limit=12", token),
        apiClient.get<TaskQueue>("/ops/task-queue", token),
      ]);
      setStats(statsData); setRfqs(rfqData); setQueue(queueData);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "營運資料載入失敗"); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  const priority = useMemo(() => [...rfqs].filter((item) => item.status === "new" || item.status === "assigned").sort((a, b) => Number(b.acceptance_sla_breached) - Number(a.acceptance_sla_breached) || Number(b.priority === "urgent") - Number(a.priority === "urgent") || new Date(a.created_at).getTime() - new Date(b.created_at).getTime()).slice(0, 5), [rfqs]);
  const stages = [
    ["網站收到", stats?.total ?? 0, "近 30 天有效詢價"],
    ["已寄確認", stats?.acknowledged ?? 0, "系統可驗證送達"],
    ["業務接手", stats?.accepted ?? 0, "已確認內部交接"],
    ["人工回覆", stats?.verified_responses ?? 0, "僅計可驗證回覆"],
  ] as const;
  const maxStage = Math.max(...stages.map((stage) => stage[1]), 1);

  return <div className="space-y-5">
    <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-cyan-950 to-teal-800 p-6 text-white shadow-sm"><div className="flex flex-wrap items-center justify-between gap-5"><div><p className="text-xs font-semibold tracking-[0.18em] text-cyan-200">今日工作 · 網站詢價交接</p><h1 className="mt-2 text-3xl font-bold">{user?.full_name ? `${user.full_name}，` : ""}先完成 {queue?.total_open ?? 0} 項可確認工作</h1><p className="mt-2 max-w-3xl text-sm text-cyan-50/85">ForgeBase 負責把網站內容、訪客足跡與詢價完整交給業務；成交與線下聯繫留在公司原有作業，不要求業務重複回填。</p></div><div className="flex gap-2"><Button asChild className="bg-white text-slate-900 hover:bg-cyan-50"><Link href="/dashboard/tasks">開始處理 <ArrowRight className="ml-2 h-4 w-4" /></Link></Button><Button variant="outline" className="border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />更新</Button></div></div></div>
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {[
        { label: "今日必須處理", value: queue?.total_open ?? "—", note: "未分派、待接手與待核准", Icon: ClipboardList },
        { label: "新詢價未分派", value: stats?.unassigned ?? "—", note: "主管需指定負責業務", Icon: MailCheck },
        { label: "等待業務接手", value: stats?.awaiting_acceptance ?? "—", note: `${stats?.overdue_acceptance ?? 0} 筆已逾期`, Icon: UserRoundCheck },
        { label: "近 30 天已接手", value: stats?.accepted ?? "—", note: "完成網站到業務的交接", Icon: CheckCircle2 },
      ].map(({ label, value, note, Icon }) => <Card key={label}><CardContent className="flex items-start justify-between p-5"><div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-bold">{value}</p><p className="mt-1 text-xs text-muted-foreground">{note}</p></div><Icon className="h-5 w-5 text-primary" /></CardContent></Card>)}
    </div>

    <div className="grid gap-5 xl:grid-cols-[1.35fr_0.85fr]">
      <Card><CardHeader className="flex-row items-center justify-between"><div><CardTitle>優先承接的詢價</CardTitle><p className="mt-1 text-sm text-muted-foreground">依接手逾期、緊急程度與收到時間排序</p></div><Button asChild variant="outline" size="sm"><Link href="/dashboard/rfqs">查看全部</Link></Button></CardHeader><CardContent>{priority.length === 0 ? <div className="rounded-lg bg-muted/40 py-10 text-center text-sm text-muted-foreground">目前沒有等待承接的詢價</div> : <div className="space-y-2">{priority.map((rfq) => <Link key={rfq.id} href={`/dashboard/rfqs/${rfq.id}`} className={`flex flex-wrap items-center justify-between gap-3 rounded-lg border p-4 transition hover:border-primary/40 hover:bg-muted/30 ${rfq.acceptance_sla_breached ? "border-red-200 bg-red-50/50" : ""}`}><div><p className="font-semibold">{rfq.contact?.company_name || rfq.contact?.full_name || "未填買家公司"}</p><p className="mt-1 text-xs text-muted-foreground">{rfq.rfq_number} · {rfq.contact?.country || "地區未填"} · {STATUS_LABEL[rfq.status]}</p></div><div className="text-right"><p className={rfq.acceptance_sla_breached ? "text-sm font-semibold text-red-600" : "text-sm font-medium"}>{!rfq.assigned_to_name ? "尚未分派" : rfq.acceptance_sla_breached ? "接手已逾期" : `負責：${rfq.assigned_to_name}`}</p><p className="mt-1 text-xs text-muted-foreground">{rfq.acceptance_due_at ? `期限 ${dateTime(rfq.acceptance_due_at)}` : `收到 ${dateTime(rfq.created_at)}`}</p></div></Link>)}</div>}</CardContent></Card>

      <Card><CardHeader><CardTitle>今日工作分類</CardTitle><p className="text-sm text-muted-foreground">只顯示系統能由資料判定的待辦</p></CardHeader><CardContent className="space-y-3">{queue?.tasks.map((task) => <div key={task.type} className="flex items-center justify-between rounded-lg border p-4"><span className="text-sm font-medium">{task.title}</span><span className={`rounded-full px-2.5 py-1 text-xs font-bold ${task.count ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-700"}`}>{task.count ? `${task.count} 項` : "完成"}</span></div>)}<Button asChild className="w-full"><Link href="/dashboard/tasks">打開今日工作</Link></Button></CardContent></Card>
    </div>

    <Card><CardHeader><CardTitle>近 30 天網站詢價交接</CardTitle><p className="text-sm text-muted-foreground">這不是成交漏斗；只呈現 ForgeBase 能由網站與系統事件確認的階段。</p></CardHeader><CardContent><div className="grid gap-5 md:grid-cols-4">{stages.map(([label, value, note], index) => <div key={label} className="relative"><div className="mb-2 flex items-end justify-between"><span className="text-sm font-semibold">{index + 1}. {label}</span><span className="text-2xl font-bold">{value}</span></div><div className="h-2 overflow-hidden rounded-full bg-muted"><div className="h-full rounded-full bg-primary" style={{ width: `${Math.max(value ? 8 : 0, Math.round(value / maxStage * 100))}%` }} /></div><p className="mt-2 text-xs text-muted-foreground">{note}</p></div>)}</div></CardContent></Card>

    <div className="grid gap-4 md:grid-cols-3">{[
      ["準備網站與產品", "先維護產品、頁面、多語內容，讓訪客看懂能否合作。", "/dashboard/content"],
      ["觀察訪客與來源", "查看第一方訪客旅程、來源與客服對話，不假裝知道買家意圖。", "/dashboard/buyers"],
      ["承接網站詢價", "確認表單內容、分派業務並留下可稽核的接手時間。", "/dashboard/rfqs"],
    ].map(([title, body, href]) => <Card key={title}><CardContent className="p-5"><p className="font-semibold">{title}</p><p className="mt-2 min-h-10 text-sm text-muted-foreground">{body}</p><Link href={href} className="mt-4 inline-flex items-center text-sm font-semibold text-primary">前往工作區 <ArrowRight className="ml-1 h-4 w-4" /></Link></CardContent></Card>)}</div>
  </div>;
}
