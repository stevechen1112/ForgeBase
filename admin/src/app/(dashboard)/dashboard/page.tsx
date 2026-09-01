"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  ArrowUpRight,
  Bell,
  CalendarClock,
  CheckCircle2,
  ChevronRight,
  CircleDollarSign,
  ClipboardList,
  FileCheck2,
  ListChecks,
  PanelsTopLeft,
  RefreshCcw,
  Route,
  Sparkles,
  Trophy,
  UserPlus,
  UsersRound,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";
import { useCapabilities } from "@/lib/hooks/useCapabilities";
import { cn } from "@/lib/utils";

type ContactSummary = {
  full_name: string | null;
  company_name: string | null;
  email: string | null;
  country: string | null;
};

type RFQRow = {
  id: string;
  rfq_number: string;
  status: string;
  priority: string;
  quality_score: number | null;
  sla_breached: boolean;
  assigned_to: string | null;
  next_follow_up_at: string | null;
  deal_amount: string | null;
  deal_currency: string | null;
  created_at: string;
  contact: ContactSummary | null;
};

type FunnelData = {
  totals: { visitors: number; rfqs: number; won: number };
  conversion_rates: { visitor_to_rfq: number };
};

type TaskItem = { id?: string; rfq_number?: string; page_title?: string };
type TaskGroup = {
  type: string;
  count: number;
  items: TaskItem[];
};
type TaskQueue = { total_open: number; tasks: TaskGroup[] };
type OutcomesData = {
  funnel_status: Record<string, number>;
  next_week_suggestions: string[];
};

const STATUS_LABEL: Record<string, string> = {
  new: "新詢價",
  assigned: "已分派",
  in_progress: "洽談中",
  reviewing: "評估中",
  quoted: "已報價",
  negotiation: "議價中",
  won: "已成交",
  lost: "未成交",
  expired: "已過期",
  closed: "已結案",
};

const CLOSED = new Set(["won", "lost", "expired", "closed"]);
const STATUS_ORDER = ["new", "assigned", "in_progress", "reviewing", "quoted", "negotiation", "won"];

function displayBuyer(rfq: RFQRow): string {
  return rfq.contact?.company_name || rfq.contact?.full_name || rfq.rfq_number;
}

function relativeTime(iso: string): string {
  const minutes = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 60000));
  if (minutes < 60) return `${Math.max(1, minutes)} 分鐘前`;
  if (minutes < 1440) return `${Math.floor(minutes / 60)} 小時前`;
  return `${Math.floor(minutes / 1440)} 天前`;
}

function isOverdue(rfq: RFQRow): boolean {
  if (CLOSED.has(rfq.status)) return false;
  return Boolean(
    rfq.sla_breached ||
      (rfq.next_follow_up_at && new Date(rfq.next_follow_up_at).getTime() < Date.now()),
  );
}

function priorityText(rfq: RFQRow): string {
  if (isOverdue(rfq)) return "已逾期，請優先回覆";
  if (!rfq.assigned_to && rfq.status === "new") return "新詢價，尚未分派";
  if (rfq.next_follow_up_at) {
    return `跟進時間 ${new Date(rfq.next_follow_up_at).toLocaleString("zh-TW", {
      month: "numeric",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })}`;
  }
  return `詢價完整度 ${rfq.quality_score ?? 0} 分`;
}

export default function DashboardPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const { hasFeature, isLoading: featuresLoading } = useCapabilities();
  const hasOutcomes = !featuresLoading && hasFeature("outcomes_dashboard");
  const [rfqs, setRfqs] = useState<RFQRow[]>([]);
  const [funnel, setFunnel] = useState<FunnelData | null>(null);
  const [queue, setQueue] = useState<TaskQueue | null>(null);
  const [outcomes, setOutcomes] = useState<OutcomesData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    if (!token || featuresLoading) return;
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      apiClient.get<RFQRow[]>("/tracking/rfqs?limit=200", token),
      apiClient.get<FunnelData>("/tracking/analytics/funnel?days=30", token),
      apiClient.get<TaskQueue>("/ops/task-queue", token),
      hasOutcomes
        ? apiClient.get<OutcomesData>("/tracking/outcomes", token)
        : Promise.resolve(null),
    ]);

    const [rfqResult, funnelResult, queueResult, outcomesResult] = results;
    if (rfqResult.status === "fulfilled") setRfqs(Array.isArray(rfqResult.value) ? rfqResult.value : []);
    else setError(rfqResult.reason instanceof Error ? rfqResult.reason.message : "無法載入詢價資料");
    setFunnel(funnelResult.status === "fulfilled" ? funnelResult.value : null);
    setQueue(queueResult.status === "fulfilled" ? queueResult.value : null);
    setOutcomes(
      outcomesResult.status === "fulfilled" && outcomesResult.value
        ? outcomesResult.value
        : null,
    );
    setLoading(false);
  }, [featuresLoading, hasOutcomes, token]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const dashboard = useMemo(() => {
    const now = new Date();
    const rollingStart = now.getTime() - 30 * 24 * 60 * 60 * 1000;
    const recent = rfqs.filter((rfq) => new Date(rfq.created_at).getTime() >= rollingStart);
    const open = recent.filter((rfq) => !CLOSED.has(rfq.status));
    const newUnassigned = open.filter((rfq) => rfq.status === "new" && !rfq.assigned_to).length;
    const highAttention = open.filter((rfq) => (rfq.quality_score ?? 0) >= 80).length;
    const won = recent.filter((rfq) => rfq.status === "won").length;
    const overdue = open.filter(isOverdue).length;

    const itemKeys = new Set<string>();
    queue?.tasks.forEach((task) => {
      task.items.forEach((item, index) => itemKeys.add(item.id || `${task.type}-${index}`));
    });
    const todayTasks = itemKeys.size || queue?.total_open || 0;

    const priorities = [...open]
      .sort((a, b) => {
        const rank = (rfq: RFQRow) =>
          (isOverdue(rfq) ? 1000 : 0) +
          (!rfq.assigned_to && rfq.status === "new" ? 500 : 0) +
          (rfq.priority === "urgent" ? 200 : rfq.priority === "high" ? 100 : 0) +
          (rfq.quality_score ?? 0);
        return rank(b) - rank(a);
      })
      .slice(0, 4);

    const statusCounts = recent.reduce<Record<string, number>>((acc, rfq) => {
      acc[rfq.status] = (acc[rfq.status] ?? 0) + 1;
      return acc;
    }, {});
    const atOrBeyond = (status: string) => {
      const threshold = STATUS_ORDER.indexOf(status);
      return recent.filter((rfq) => STATUS_ORDER.indexOf(rfq.status) >= threshold).length;
    };
    const pipeline = [
      { label: "有效詢價", value: recent.length },
      { label: "已報價", value: atOrBeyond("quoted") },
      { label: "議價中", value: statusCounts.negotiation ?? 0 },
      { label: "已成交", value: won },
    ];

    const days = Array.from({ length: 7 }, (_, index) => {
      const date = new Date(now);
      date.setHours(0, 0, 0, 0);
      date.setDate(date.getDate() - (6 - index));
      const next = new Date(date);
      next.setDate(next.getDate() + 1);
      const rows = rfqs.filter((rfq) => {
        const timestamp = new Date(rfq.created_at).getTime();
        return timestamp >= date.getTime() && timestamp < next.getTime();
      });
      return {
        label: index === 6 ? "今天" : date.toLocaleDateString("zh-TW", { weekday: "short" }),
        total: rows.length,
        overdue: rows.filter(isOverdue).length,
      };
    });

    return { recent, newUnassigned, highAttention, won, overdue, todayTasks, priorities, pipeline, days };
  }, [queue, rfqs]);

  const maxPipeline = Math.max(1, ...dashboard.pipeline.map((item) => item.value));
  const maxDay = Math.max(1, ...dashboard.days.map((item) => item.total));
  const demoVisible = rfqs.some((rfq) => rfq.rfq_number.startsWith("DEMO-"));
  const userName = user?.full_name || user?.email?.split("@")[0] || "主管";

  const kpis = [
    {
      label: "今日必須完成",
      value: dashboard.todayTasks,
      note: `其中 ${dashboard.overdue} 項已逾期`,
      icon: ListChecks,
      color: "border-l-[#176c89] bg-cyan-50 text-[#176c89]",
    },
    {
      label: "新詢價待分派",
      value: dashboard.newUnassigned,
      note: dashboard.newUnassigned ? "請先確認負責業務" : "目前皆已分派",
      icon: UserPlus,
      color: "border-l-violet-500 bg-violet-50 text-violet-600",
    },
    {
      label: "高關注買家",
      value: dashboard.highAttention,
      note: "詢價完整度 80 分以上",
      icon: UsersRound,
      color: "border-l-amber-500 bg-amber-50 text-amber-600",
    },
    {
      label: "近 30 天已成交",
      value: dashboard.won,
      note: dashboard.recent.length ? `詢價成交率 ${Math.round((dashboard.won / dashboard.recent.length) * 100)}%` : "近 30 天尚無詢價",
      icon: Trophy,
      color: "border-l-emerald-500 bg-emerald-50 text-emerald-600",
    },
  ];

  return (
    <div className="space-y-5 pb-10">
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
      )}

      <section className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#114c68] to-[#247e8d] px-6 py-6 text-white shadow-sm sm:px-8">
        <div className="absolute -right-12 -top-20 h-56 w-56 rounded-full bg-white/10 blur-2xl" />
        <div className="relative flex flex-wrap items-start justify-between gap-5">
          <div>
            <div className="mb-2 flex flex-wrap items-center gap-2 text-sm font-semibold text-cyan-100">
              <span>每日營運總覽</span>
              {demoVisible && <Badge className="border border-white/25 bg-white/15 text-white hover:bg-white/15">展示資料</Badge>}
            </div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl">早安，{userName}！先處理最接近成交的工作。</h1>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-cyan-50 sm:text-base">
              今天有 <strong>{dashboard.todayTasks} 項工作</strong>
              {dashboard.overdue > 0 && <>，其中 <strong>{dashboard.overdue} 項已逾期</strong></>}
              ；近 30 天共 {dashboard.recent.length} 筆詢價，已有 {dashboard.won} 筆成交。
              {funnel && <> 近 30 天另有 {funnel.totals.visitors} 位訪客，訪客轉詢價率 {funnel.conversion_rates.visitor_to_rfq}%。</>}
            </p>
          </div>
          <div className="flex gap-2">
            <Button asChild className="bg-white text-[#155a73] hover:bg-cyan-50">
              <Link href="/dashboard/tasks">開始處理 <ChevronRight className="ml-1 h-4 w-4" /></Link>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="border border-white/25 text-white hover:bg-white/10 hover:text-white"
              onClick={() => void loadData()}
              disabled={loading}
              aria-label="重新整理營運資料"
            >
              <RefreshCcw className={cn("h-4 w-4", loading && "animate-spin")} />
            </Button>
          </div>
        </div>
      </section>

      <section>
        <div className="mb-3 flex items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-slate-900">今天先看這四件事</h2>
            <p className="text-sm text-slate-500">只呈現會影響回覆速度與成交的關鍵數字</p>
          </div>
          {demoVisible && <span className="hidden text-xs text-slate-500 sm:block">資料皆為 Demo 租戶合成內容，不會寄出郵件</span>}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {kpis.map(({ label, value, note, icon: Icon, color }) => (
            <Card key={label} className={cn("border-l-4 shadow-sm", color.split(" ")[0])}>
              <CardContent className="flex items-start justify-between p-5">
                <div>
                  <p className="text-sm font-medium text-slate-600">{label}</p>
                  <p className="mt-2 text-3xl font-bold tracking-tight text-slate-950">{loading ? "—" : value}</p>
                  <p className="mt-1 text-xs text-slate-500">{note}</p>
                </div>
                <div className={cn("flex h-10 w-10 items-center justify-center rounded-xl", color.split(" ").slice(1).join(" "))}>
                  <Icon className="h-5 w-5" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between border-b pb-4">
            <div>
              <CardTitle className="text-lg">主管優先工作</CardTitle>
              <p className="mt-1 text-sm text-slate-500">依逾期、待分派、優先度與詢價完整度排序</p>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard/tasks">全部待辦</Link>
            </Button>
          </CardHeader>
          <CardContent className="p-4">
            {loading ? (
              <p className="py-12 text-center text-sm text-slate-500">載入工作中…</p>
            ) : dashboard.priorities.length === 0 ? (
              <div className="flex flex-col items-center py-10 text-center">
                <CheckCircle2 className="mb-3 h-9 w-9 text-emerald-500" />
                <p className="font-semibold">目前沒有急迫詢價</p>
                <p className="mt-1 text-sm text-slate-500">新詢價進來後會自動依優先度出現在這裡</p>
              </div>
            ) : (
              <div className="space-y-2">
                {dashboard.priorities.map((rfq) => (
                  <Link
                    key={rfq.id}
                    href={`/dashboard/rfqs/${rfq.id}`}
                    className="flex items-center gap-3 rounded-xl border border-slate-200 px-4 py-3 transition-colors hover:border-[#63aabd] hover:bg-cyan-50/40"
                  >
                    <div className={cn(
                      "flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-sm font-bold",
                      isOverdue(rfq) ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700",
                    )}>
                      {isOverdue(rfq) ? "急" : `${rfq.quality_score ?? 0}`}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate font-semibold text-slate-950">{displayBuyer(rfq)}</p>
                        <Badge variant="outline" className="h-5 text-[10px]">{STATUS_LABEL[rfq.status] || rfq.status}</Badge>
                      </div>
                      <p className={cn("mt-0.5 text-xs", isOverdue(rfq) ? "font-medium text-red-700" : "text-slate-500")}>{priorityText(rfq)}</p>
                    </div>
                    <Button variant="outline" size="sm" className="shrink-0">處理</Button>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b pb-4">
            <CardTitle className="text-lg">近 30 天商機進度</CardTitle>
            <p className="mt-1 text-sm text-slate-500">從有效詢價一路看到成交</p>
          </CardHeader>
          <CardContent className="space-y-4 p-5">
            {dashboard.pipeline.map((item, index) => (
              <div key={item.label}>
                <div className="mb-1.5 flex items-center justify-between text-sm">
                  <span className="font-medium text-slate-700">{item.label}</span>
                  <strong className="text-slate-950">{loading ? "—" : item.value}</strong>
                </div>
                <div className="h-3 overflow-hidden rounded-full bg-slate-100">
                  <div
                    className={cn("h-full rounded-full", index === 3 ? "bg-emerald-600" : "bg-[#247d69]")}
                    style={{ width: `${Math.max(item.value ? 8 : 0, (item.value / maxPipeline) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
            <Button variant="outline" className="w-full" asChild>
              <Link href={hasOutcomes ? "/dashboard/outcomes" : "/dashboard/rfqs"}>
                {hasOutcomes ? "查看成交成果" : "查看全部詢價"} <ArrowUpRight className="ml-1 h-4 w-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.65fr)_minmax(300px,0.85fr)]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between border-b pb-4">
            <div>
              <CardTitle className="text-lg">近 7 天詢價工作量</CardTitle>
              <p className="mt-1 text-sm text-slate-500">紅色代表目前仍逾期的詢價</p>
            </div>
            <CalendarClock className="h-5 w-5 text-slate-400" />
          </CardHeader>
          <CardContent className="p-5">
            <div className="flex h-44 items-end gap-3" aria-label="近 7 天詢價工作量長條圖">
              {dashboard.days.map((day) => {
                const height = Math.max(day.total ? 18 : 4, (day.total / maxDay) * 100);
                const overdueHeight = day.total ? (day.overdue / day.total) * 100 : 0;
                return (
                  <div key={day.label} className="flex h-full min-w-0 flex-1 flex-col justify-end text-center">
                    <span className="mb-1 text-xs font-bold text-slate-700">{day.total}</span>
                    <div className="relative mx-auto w-full max-w-14 overflow-hidden rounded-t-md bg-[#2c8297]" style={{ height: `${height}%` }}>
                      {overdueHeight > 0 && <div className="absolute bottom-0 w-full bg-red-500" style={{ height: `${overdueHeight}%` }} />}
                    </div>
                    <span className="mt-2 truncate text-[11px] text-slate-500">{day.label}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b pb-4">
            <CardTitle className="flex items-center gap-2 text-lg"><Sparkles className="h-5 w-5 text-amber-500" />建議下一步</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 p-5">
            {(outcomes?.next_week_suggestions?.length
              ? outcomes.next_week_suggestions
              : ["先完成逾期詢價回覆", "確認新詢價的負責業務", "檢查本週待發布內容"]
            ).slice(0, 3).map((suggestion, index) => (
              <div key={`${suggestion}-${index}`} className="flex gap-3 rounded-xl bg-slate-50 p-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-[#176c89] text-xs font-bold text-white">{index + 1}</span>
                <p className="text-sm leading-6 text-slate-700">{suggestion}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-5 lg:grid-cols-[minmax(0,1.5fr)_minmax(280px,0.7fr)]">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between border-b pb-4">
            <div>
              <CardTitle className="text-lg">最新詢價</CardTitle>
              <p className="mt-1 text-sm text-slate-500">最近收到的買家需求與目前進度</p>
            </div>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard/rfqs">查看全部 <ArrowUpRight className="ml-1 h-4 w-4" /></Link>
            </Button>
          </CardHeader>
          <CardContent className="p-0">
            {rfqs.slice(0, 6).map((rfq) => (
              <Link key={rfq.id} href={`/dashboard/rfqs/${rfq.id}`} className="flex items-center gap-3 border-b px-5 py-3 last:border-b-0 hover:bg-slate-50">
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-[#176c89]"><ClipboardList className="h-4 w-4" /></div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="truncate text-sm font-semibold">{displayBuyer(rfq)}</p>
                    <Badge variant="outline" className="h-5 text-[10px]">{STATUS_LABEL[rfq.status] || rfq.status}</Badge>
                  </div>
                  <p className="mt-0.5 truncate text-xs text-slate-500">{rfq.rfq_number}・{relativeTime(rfq.created_at)}</p>
                </div>
                <ChevronRight className="h-4 w-4 text-slate-400" />
              </Link>
            ))}
            {!loading && rfqs.length === 0 && <p className="py-12 text-center text-sm text-slate-500">尚無詢價資料</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b pb-4"><CardTitle className="text-lg">快速入口</CardTitle></CardHeader>
          <CardContent className="space-y-1 p-3">
            {[
              { label: "買家管線", href: "/dashboard/buyers", icon: Route },
              { label: "內容中心", href: "/dashboard/content", icon: PanelsTopLeft },
              { label: "今日待辦", href: "/dashboard/tasks", icon: FileCheck2 },
              { label: "通知中心", href: "/dashboard/notifications", icon: Bell },
            ].map(({ label, href, icon: Icon }) => (
              <Link key={label} href={href} className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium hover:bg-slate-50">
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-100"><Icon className="h-4 w-4 text-slate-600" /></span>
                {label}<ChevronRight className="ml-auto h-4 w-4 text-slate-400" />
              </Link>
            ))}
          </CardContent>
        </Card>
      </section>

      {demoVisible && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-cyan-200 bg-cyan-50/70 px-4 py-3 text-sm text-slate-700">
          <span className="flex items-center gap-2"><CircleDollarSign className="h-4 w-4 text-[#176c89]" />目前為展示租戶：資料可操作示範，但系統不會因這批資料自動寄信。</span>
          <span className="text-xs text-slate-500">所有展示信箱皆使用 example.com</span>
        </div>
      )}
    </div>
  );
}
