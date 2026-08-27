"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertCircle, CheckCircle2, Clock, Database, RefreshCw, RotateCcw, ServerCog, ShieldCheck, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type OperationalJobItem, type OperationalJobSummary, type SystemHealth } from "@/lib/api/platform-admin";

function formatUptime(seconds: number) {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return hours ? `${hours} 小時 ${minutes} 分` : `${minutes} 分鐘`;
}

export default function PlatformHealthPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [jobs, setJobs] = useState<OperationalJobSummary | null>(null);
  const [failedJobs, setFailedJobs] = useState<OperationalJobItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [systemHealth, jobSummary, failed] = await Promise.all([
        platformAdminApi.systemHealth(token),
        platformAdminApi.operationalJobSummary(token),
        platformAdminApi.operationalJobs(token),
      ]);
      setHealth(systemHealth);
      setJobs(jobSummary);
      setFailedJobs(failed.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取系統狀態");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function retryJob(id: string) {
    if (!token) return;
    setRetrying(id);
    try {
      await platformAdminApi.retryOperationalJob(token, id);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "重試失敗");
    } finally {
      setRetrying(null);
    }
  }

  const runtimeHealthy = health?.status === "healthy" && jobs?.healthy !== false;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">系統健康與對外測試封板</h1>
          <p className="mt-1 text-sm text-muted-foreground">系統可運作不等於可開放未知流量；下方分開呈現兩種狀態。</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />重新檢查
        </Button>
      </div>

      {error && <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{error}</div>}

      {health && (
        <div className="grid gap-5 lg:grid-cols-2">
          <section className="rounded-xl border bg-card p-5 shadow-sm">
            <div className="mb-4 flex items-center gap-2"><Activity className="h-5 w-5" /><h2 className="font-semibold">系統運作狀態</h2><span className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${runtimeHealthy ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{runtimeHealthy ? "正常" : "需處理"}</span></div>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="flex items-center gap-2 text-muted-foreground"><Database className="h-4 w-4" />資料庫</span><span>{health.database}</span></div>
              <div className="flex justify-between"><span className="flex items-center gap-2 text-muted-foreground"><Clock className="h-4 w-4" />API 已運作</span><span>{formatUptime(health.uptime_seconds)}</span></div>
              <div className="flex justify-between"><span className="text-muted-foreground">背景工作</span><span>{jobs?.healthy === false ? "有異常" : "正常"}</span></div>
            </div>
          </section>

          <section className={`rounded-xl border p-5 shadow-sm ${health.external_test.ready ? "border-green-300 bg-green-50/40" : "border-amber-300 bg-amber-50/50"}`}>
            <div className="mb-4 flex items-center gap-2"><ShieldCheck className="h-5 w-5" /><h2 className="font-semibold">正式外部測試 Gate</h2><span className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${health.external_test.ready ? "bg-green-100 text-green-700" : "bg-amber-100 text-amber-800"}`}>{health.external_test.ready ? "可開放" : `尚缺 ${health.external_test.blockers.length} 項`}</span></div>
            <div className="space-y-2">
              {Object.entries(health.external_test.checks).map(([key, check]) => (
                <div key={key} className="flex items-center justify-between gap-3 rounded-lg bg-background/70 px-3 py-2 text-sm">
                  <span>{check.label}</span>
                  {check.ok ? <span className="flex items-center gap-1 text-green-700"><CheckCircle2 className="h-4 w-4" />完成</span> : <span className="flex items-center gap-1 text-amber-700"><XCircle className="h-4 w-4" />阻擋</span>}
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {jobs && (
        <section className="rounded-xl border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-center gap-2"><ServerCog className="h-5 w-5" /><h2 className="font-semibold">背景工作佇列</h2></div>
          <div className="grid gap-3 sm:grid-cols-5">
            {[["等待", "pending"], ["重試", "retry"], ["處理中", "processing"], ["完成", "completed"], ["失敗", "failed"]].map(([label, key]) => <div key={key} className="rounded-lg border bg-muted/20 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-semibold">{jobs.counts[key] ?? 0}</p></div>)}
          </div>
        </section>
      )}

      <section className="overflow-hidden rounded-xl border bg-card shadow-sm">
        <div className="border-b px-5 py-4"><h2 className="font-semibold">失敗工作</h2></div>
        {failedJobs.length === 0 ? <p className="p-5 text-sm text-muted-foreground">目前沒有失敗工作。</p> : <div className="divide-y">{failedJobs.map(job => <div key={job.id} className="flex items-center gap-4 p-4 text-sm"><span className="font-mono text-xs">{job.job_type}</span><span className="min-w-0 flex-1 truncate text-red-600">{job.last_error || "未知錯誤"}</span><Button variant="outline" size="sm" onClick={() => void retryJob(job.id)} disabled={retrying === job.id}><RotateCcw className={`mr-1 h-3.5 w-3.5 ${retrying === job.id ? "animate-spin" : ""}`} />重試</Button></div>)}</div>}
      </section>
    </div>
  );
}
