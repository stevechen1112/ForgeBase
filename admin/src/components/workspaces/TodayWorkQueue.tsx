"use client";

import { useCallback, useEffect, useState, type ElementType } from "react";
import Link from "next/link";
import {
  AlarmClock,
  ArrowRight,
  Bell,
  ClipboardList,
  FileCheck,
  LayoutDashboard,
  RefreshCw,
  UserRoundPlus,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";

type TaskItem = {
  id?: string;
  rfq_number?: string;
  page_title?: string;
  slug?: string;
  created_at?: string;
  acceptance_due_at?: string;
  overdue?: boolean;
};

type Task = {
  type: string;
  title: string;
  count: number;
  severity: "high" | "medium" | "low" | "none";
  items: TaskItem[];
  link: string | null;
};

type TaskQueue = { generated_at: string; total_open: number; tasks: Task[] };

const TYPE_ICON: Record<string, ElementType> = {
  rfq_unassigned: UserRoundPlus,
  rfq_awaiting_acceptance: AlarmClock,
  content_pending_approval: FileCheck,
};

const SEVERITY_STYLE: Record<Task["severity"], string> = {
  high: "border-red-200 bg-red-50 text-red-700",
  medium: "border-amber-200 bg-amber-50 text-amber-800",
  low: "border-sky-200 bg-sky-50 text-sky-700",
  none: "border-slate-200 bg-slate-50 text-slate-600",
};

const SEVERITY_LABEL: Record<Task["severity"], string> = {
  high: "優先處理",
  medium: "今天處理",
  low: "安排處理",
  none: "待確認",
};

function itemHref(item: TaskItem, fallback: string | null) {
  if (item.rfq_number && item.id) return `/dashboard/rfqs/${item.id}`;
  if (item.page_title && item.id) return `/dashboard/pages/${item.id}/edit`;
  return fallback ?? "/dashboard";
}

function itemMeta(item: TaskItem) {
  if (item.rfq_number) {
    if (item.acceptance_due_at) {
      const when = new Date(item.acceptance_due_at).toLocaleString("zh-TW");
      return item.overdue ? `接手已逾期・${when}` : `接手期限・${when}`;
    }
    return item.created_at ? `收到於 ${new Date(item.created_at).toLocaleString("zh-TW")}` : "新詢價";
  }
  return item.slug ? `/${item.slug}` : "待內容確認";
}

export function TodayWorkQueue() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [queue, setQueue] = useState<TaskQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      setQueue(await apiClient.get<TaskQueue>("/ops/task-queue", token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "今日工作載入失敗");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const tasks = [...(queue?.tasks ?? [])].sort((left, right) => {
    const order: Record<Task["severity"], number> = { high: 0, medium: 1, low: 2, none: 3 };
    return order[left.severity] - order[right.severity];
  });
  const urgentCount = tasks.filter((task) => task.severity === "high").reduce((sum, task) => sum + task.count, 0);
  const assignmentCount = tasks.filter((task) => task.type === "rfq_unassigned").reduce((sum, task) => sum + task.count, 0);
  const acceptanceCount = tasks.filter((task) => task.type === "rfq_awaiting_acceptance").reduce((sum, task) => sum + task.count, 0);

  return (
    <div className="space-y-5">
      <section className="rounded-[14px] bg-gradient-to-r from-[#123b55] to-[#087b8f] px-7 py-6 text-white shadow-[0_10px_28px_rgba(20,38,57,.08)]">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div>
            <p className="text-[13px] font-extrabold text-cyan-100">今日工作</p>
            <h1 className="mt-1 text-[29px] font-black">先完成今天需要處理的事</h1>
            <p className="mt-2 text-[15px] text-cyan-50">
              只列出系統能明確確認的待辦：詢價分派、業務接手與內容核准；不要求回填電話、報價或成交。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button asChild className="h-10 bg-white text-[#087b8f] hover:bg-cyan-50">
              <Link href="/dashboard"><LayoutDashboard className="mr-2 h-4 w-4" />回營運總覽</Link>
            </Button>
            <Button asChild variant="outline" className="h-10 border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white">
              <Link href="/dashboard/notifications"><Bell className="mr-2 h-4 w-4" />通知中心</Link>
            </Button>
            <Button variant="outline" size="icon" className="h-10 border-white/40 bg-white/10 text-white hover:bg-white/20 hover:text-white" onClick={load} disabled={loading} aria-label="重新整理今日工作">
              <RefreshCw className={loading ? "h-4 w-4 animate-spin" : "h-4 w-4"} />
            </Button>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-3">
        {[
          ["優先處理", urgentCount, "先處理逾期或高優先案件", "border-l-red-500"],
          ["新詢價待分派", assignmentCount, "主管指定負責業務", "border-l-amber-500"],
          ["等待業務接手", acceptanceCount, "確認案件已由業務接手", "border-l-emerald-600"],
        ].map(([label, value, note, border]) => (
          <Card key={String(label)} className={`border-l-4 ${border}`}>
            <CardContent className="p-5">
              <p className="text-sm font-bold text-slate-600">{label}</p>
              <p className="mt-2 text-3xl font-black text-[#10263b]">{value}</p>
              <p className="mt-2 text-sm text-slate-500">{note}</p>
            </CardContent>
          </Card>
        ))}
      </section>

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <section className="rounded-[14px] border bg-white shadow-sm">
        <div className="flex flex-wrap items-end justify-between gap-3 border-b px-6 py-5">
          <div>
            <h2 className="text-xl font-extrabold text-[#10263b]">依優先順序處理</h2>
            <p className="mt-1 text-sm text-slate-500">先做紅色與橘色項目；每筆案件可直接開啟處理，不必先找功能。</p>
          </div>
          <Badge className="border border-[#b9e1e4] bg-[#e8f6f7] px-3 py-1 text-sm text-[#087b8f]">共 {queue?.total_open ?? 0} 項待辦</Badge>
        </div>

        <div className="divide-y">
          {tasks.length === 0 && !loading && (
            <div className="px-6 py-12 text-center">
              <ClipboardList className="mx-auto h-8 w-8 text-emerald-600" />
              <h3 className="mt-3 font-extrabold text-[#10263b]">今天沒有需要系統協助處理的工作</h3>
              <p className="mt-1 text-sm text-slate-500">您可回營運總覽查看網站承接與詢價交接的整體狀況。</p>
            </div>
          )}

          {tasks.length === 0 && loading && (
            <div className="px-6 py-12 text-center text-sm text-slate-500">正在整理今天需要處理的工作…</div>
          )}

          {tasks.map((task) => {
            const Icon = TYPE_ICON[task.type] ?? ClipboardList;
            return (
              <div key={task.type} className="px-6 py-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#e8f6f7] text-[#087b8f]"><Icon className="h-5 w-5" /></span>
                    <div>
                      <h3 className="font-extrabold text-[#10263b]">{task.title}</h3>
                      <p className="text-sm text-slate-500">{SEVERITY_LABEL[task.severity]}・{task.count} 項</p>
                    </div>
                  </div>
                  <Badge className={`border ${SEVERITY_STYLE[task.severity]}`}>{SEVERITY_LABEL[task.severity]}</Badge>
                </div>

                {task.items.length > 0 ? (
                  <div className="mt-4 space-y-2">
                    {task.items.map((item, index) => (
                      <div key={item.id || `${task.type}-${index}`} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-slate-50/70 px-4 py-3">
                        <div className="min-w-0">
                          <p className="font-bold text-[#10263b]">{item.rfq_number ?? item.page_title ?? task.title}</p>
                          <p className={item.overdue ? "mt-1 text-sm font-semibold text-red-600" : "mt-1 text-sm text-slate-500"}>{itemMeta(item)}</p>
                        </div>
                        <Button asChild size="sm" className="bg-[#087b8f] hover:bg-[#056b7c]">
                          <Link href={itemHref(item, task.link)}>處理<ArrowRight className="ml-2 h-4 w-4" /></Link>
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : task.count > 0 ? (
                  <div className="mt-4 rounded-xl border border-dashed px-4 py-3 text-sm text-slate-500">有 {task.count} 項待辦，請開啟處理頁查看完整清單。</div>
                ) : (
                  <p className="mt-4 text-sm text-slate-500">目前沒有此類待辦。</p>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {queue && <p className="text-right text-xs text-slate-400">清單更新時間：{new Date(queue.generated_at).toLocaleString("zh-TW")}</p>}
    </div>
  );
}
