"use client";
import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, AlarmClock, Flame, Filter, FileCheck, ShieldQuestion } from "lucide-react";
import { apiClient } from "@/lib/api/client";

// 顧問 Growth Ops 工作台（實效計畫 §7.1）：一個入口清「今日必處理」
type TaskItem = Record<string, unknown> & { id?: string; rfq_number?: string; visitor_id?: string };
type Task = {
  type: string;
  title: string;
  count: number;
  severity: "high" | "medium" | "low" | "none";
  available?: boolean;
  reason?: string;
  items: TaskItem[];
  link: string | null;
};
type TaskQueue = { generated_at: string; total_open: number; tasks: Task[] };

const TYPE_ICON: Record<string, React.ElementType> = {
  sla_breached_rfq: AlarmClock,
  hot_visitor_unassigned: Flame,
  low_quality_rfq: Filter,
  content_pending_approval: FileCheck,
  verification_anomaly: ShieldQuestion,
};

const SEVERITY_STYLE: Record<string, string> = {
  high: "bg-red-100 text-red-700",
  medium: "bg-orange-100 text-orange-700",
  low: "bg-yellow-100 text-yellow-800",
  none: "bg-muted text-muted-foreground",
};

export default function TasksPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [queue, setQueue] = useState<TaskQueue | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError(null);
    try {
      setQueue(await apiClient.get<TaskQueue>("/ops/task-queue", token));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">今日必處理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            顧問工作佇列 — 共 {queue?.total_open ?? 0} 項待辦
            {queue && <span className="ml-2 text-xs">（{new Date(queue.generated_at).toLocaleTimeString("zh-TW")} 產生）</span>}
          </p>
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

      <div className="grid gap-4">
        {queue?.tasks.map((task) => {
          const Icon = TYPE_ICON[task.type] ?? ShieldQuestion;
          const unavailable = task.available === false;
          return (
            <Card key={task.type} className={unavailable ? "opacity-60" : ""}>
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Icon className="h-4 w-4" />{task.title}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Badge className={`text-xs ${SEVERITY_STYLE[task.severity]}`}>{task.count} 項</Badge>
                    {task.link && task.count > 0 && (
                      <Button asChild variant="ghost" size="sm">
                        <Link href={task.link}>前往處理 →</Link>
                      </Button>
                    )}
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {unavailable ? (
                  <p className="text-xs text-muted-foreground">{task.reason}</p>
                ) : task.items.length > 0 ? (
                  <ul className="space-y-1.5 text-sm">
                    {task.items.map((item, i) => (
                      <li key={i} className="flex items-center gap-3">
                        {item.rfq_number ? (
                          <>
                            <Link href={`/dashboard/rfqs/${item.id}`} className="font-mono text-xs text-primary hover:underline">
                              {item.rfq_number}
                            </Link>
                            <span className="text-xs text-muted-foreground">
                              品質 {String(item.quality_score ?? "—")} 分
                              {item.sla_due_at ? `・SLA 截止 ${new Date(String(item.sla_due_at)).toLocaleString("zh-TW")}` : ""}
                            </span>
                          </>
                        ) : item.visitor_id ? (
                          <>
                            <Link href={`/dashboard/visitors/${item.visitor_id}`} className="font-mono text-xs text-primary hover:underline">
                              {String(item.visitor_id).slice(0, 8)}…
                            </Link>
                            <span className="text-xs text-muted-foreground">
                              {String(item.intent_stage)}・{String(item.intent_score)} 分
                              {item.intent_explanation ? `・${String(item.intent_explanation)}` : ""}
                            </span>
                          </>
                        ) : (
                          <span className="text-xs text-muted-foreground">{JSON.stringify(item)}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-muted-foreground">目前無待辦 ✓</p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
