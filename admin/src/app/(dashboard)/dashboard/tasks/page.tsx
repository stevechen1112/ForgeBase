"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlarmClock, ClipboardList, FileCheck, RefreshCw, UserRoundPlus } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { apiClient } from "@/lib/api/client";
import { useAuth } from "@/lib/auth/store";

type TaskItem = { id?: string; rfq_number?: string; page_title?: string; slug?: string; created_at?: string; acceptance_due_at?: string; overdue?: boolean; priority?: string };
type Task = { type: string; title: string; count: number; severity: "high" | "medium" | "low" | "none"; items: TaskItem[]; link: string | null };
type TaskQueue = { generated_at: string; total_open: number; tasks: Task[] };
const TYPE_ICON: Record<string, React.ElementType> = { rfq_unassigned: UserRoundPlus, rfq_awaiting_acceptance: AlarmClock, content_pending_approval: FileCheck };
const SEVERITY_STYLE: Record<string, string> = { high: "bg-red-100 text-red-700", medium: "bg-orange-100 text-orange-700", low: "bg-yellow-100 text-yellow-800", none: "bg-muted text-muted-foreground" };

export default function TasksPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [queue, setQueue] = useState<TaskQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError(null);
    try { setQueue(await apiClient.get<TaskQueue>("/ops/task-queue", token)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "今日工作載入失敗"); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { load(); }, [load]);

  return <div>
    <div className="mb-6 flex flex-wrap items-center justify-between gap-3"><div><h1 className="text-2xl font-bold tracking-tight">今日工作</h1><p className="mt-1 text-sm text-muted-foreground">只列出系統能確定需要處理的工作：新詢價分派、業務接手與內容核准，共 {queue?.total_open ?? 0} 項。</p></div><Button variant="outline" size="sm" onClick={load} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button></div>
    {error && <Alert variant="destructive" className="mb-4"><AlertDescription>{error}</AlertDescription></Alert>}
    <div className="grid gap-4">{queue?.tasks.map((task) => {
      const Icon = TYPE_ICON[task.type] ?? ClipboardList;
      return <Card key={task.type}><CardHeader className="pb-2"><div className="flex flex-wrap items-center justify-between gap-2"><CardTitle className="flex items-center gap-2 text-base"><Icon className="h-4 w-4" />{task.title}</CardTitle><div className="flex items-center gap-2"><Badge className={`text-xs ${SEVERITY_STYLE[task.severity]}`}>{task.count} 項</Badge>{task.link && task.count > 0 && <Button asChild variant="ghost" size="sm"><Link href={task.link}>前往處理 →</Link></Button>}</div></div></CardHeader><CardContent>{task.items.length === 0 ? <p className="text-sm text-muted-foreground">目前沒有待辦 ✓</p> : <ul className="space-y-2">{task.items.map((item, index) => <li key={item.id || index} className="flex flex-wrap items-center gap-x-3 gap-y-1 rounded-md border p-3 text-sm">{item.rfq_number ? <><Link href={`/dashboard/rfqs/${item.id}`} className="font-mono text-xs font-semibold text-primary hover:underline">{item.rfq_number}</Link><span className={item.overdue ? "font-semibold text-red-600" : "text-muted-foreground"}>{item.acceptance_due_at ? `${item.overdue ? "接手已逾期" : "接手期限"} ${new Date(item.acceptance_due_at).toLocaleString("zh-TW")}` : `收到於 ${item.created_at ? new Date(item.created_at).toLocaleString("zh-TW") : "—"}`}</span>{item.priority === "urgent" && <Badge variant="destructive">緊急</Badge>}</> : item.page_title ? <><Link href={`/dashboard/pages/${item.id}/edit`} className="font-medium text-primary hover:underline">{item.page_title}</Link><span className="text-xs text-muted-foreground">/{item.slug}</span></> : null}</li>)}</ul>}</CardContent></Card>;
    })}</div>
    {queue && <p className="mt-4 text-xs text-muted-foreground">清單更新時間：{new Date(queue.generated_at).toLocaleString("zh-TW")}</p>}
  </div>;
}
