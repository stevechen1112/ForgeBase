"use client";

import { useCallback, useEffect, useState } from "react";
import { Activity, AlertCircle, CheckCircle2, Database, RefreshCw, RotateCcw, ServerCog, ShieldCheck, Siren, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type OperationalIncident, type OperationalJobItem, type OperationalJobSummary, type ServiceLevelMetric, type ServiceLevelReport, type SystemHealth } from "@/lib/api/platform-admin";

function metricValue(metric: ServiceLevelMetric) {
  if (!metric.evaluable) return "資料量不足";
  return metric.kind === "rate" ? `${((metric.actual ?? 0) * 100).toFixed(1)}%` : String(metric.actual ?? 0);
}

function metricTarget(metric: ServiceLevelMetric) {
  return metric.kind === "rate" ? `≥ ${(metric.target * 100).toFixed(0)}%` : "= 0";
}

export default function PlatformHealthPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [jobs, setJobs] = useState<OperationalJobSummary | null>(null);
  const [failedJobs, setFailedJobs] = useState<OperationalJobItem[]>([]);
  const [slo, setSlo] = useState<ServiceLevelReport | null>(null);
  const [incidents, setIncidents] = useState<OperationalIncident[]>([]);
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const [systemHealth, jobSummary, failed, levels, incidentList] = await Promise.all([
        platformAdminApi.systemHealth(token), platformAdminApi.operationalJobSummary(token),
        platformAdminApi.operationalJobs(token), platformAdminApi.serviceLevels(token),
        platformAdminApi.operationalIncidents(token),
      ]);
      setHealth(systemHealth); setJobs(jobSummary); setFailedJobs(failed.items);
      setSlo(levels); setIncidents(incidentList.items);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取系統狀態");
    } finally { setLoading(false); }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function retryJob(id: string) {
    if (!token) return;
    setWorking(id);
    try { await platformAdminApi.retryOperationalJob(token, id); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "重試失敗"); }
    finally { setWorking(null); }
  }

  async function sampleNow() {
    if (!token) return;
    setWorking("sample");
    try { await platformAdminApi.sampleServiceLevels(token); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "取樣失敗"); }
    finally { setWorking(null); }
  }

  async function act(incident: OperationalIncident, action: "acknowledge" | "resolve") {
    if (!token) return;
    const note = notes[incident.id]?.trim() ?? "";
    if (note.length < 10) { setError("事故處置說明至少需要 10 個字元，以保留可稽核證據。"); return; }
    setWorking(incident.id);
    try {
      await platformAdminApi.actOnIncident(token, incident.id, { action, note });
      setNotes((current) => ({ ...current, [incident.id]: "" })); await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "事故處置失敗"); }
    finally { setWorking(null); }
  }

  const active = incidents.filter((incident) => incident.status !== "resolved");
  const runtimeHealthy = health?.status === "healthy" && jobs?.healthy !== false;

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold">系統健康與事故控制台</h1><p className="mt-1 text-sm text-muted-foreground">內部應用／資料庫 SLO、事故決策與外部測試 Gate 分開呈現；此處不宣稱站外 uptime。</p></div><div className="flex gap-2"><Button variant="outline" size="sm" onClick={() => void sampleNow()} disabled={loading || working === "sample"}><Activity className="mr-1.5 h-3.5 w-3.5" />立即取樣</Button><Button variant="outline" size="sm" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-1.5 h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />重新檢查</Button></div></div>
    {error && <div className="flex items-center gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{error}</div>}

    {health && <div className="grid gap-5 lg:grid-cols-2"><section className="rounded-xl border bg-card p-5 shadow-sm"><div className="mb-4 flex items-center gap-2"><Activity className="h-5 w-5" /><h2 className="font-semibold">即時運作狀態</h2><span className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${runtimeHealthy ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"}`}>{runtimeHealthy ? "正常" : "需處理"}</span></div><div className="space-y-3 text-sm"><div className="flex justify-between"><span className="flex items-center gap-2 text-muted-foreground"><Database className="h-4 w-4" />資料庫</span><span>{health.database}</span></div><div className="flex justify-between"><span className="text-muted-foreground">背景工作</span><span>{jobs?.healthy === false ? "有異常" : "正常"}</span></div></div></section><section className={`rounded-xl border p-5 shadow-sm ${health.external_test.ready ? "border-green-300 bg-green-50/40" : "border-amber-300 bg-amber-50/50"}`}><div className="mb-4 flex items-center gap-2"><ShieldCheck className="h-5 w-5" /><h2 className="font-semibold">正式外部測試 Gate</h2><span className="ml-auto text-xs font-semibold">{health.external_test.ready ? "可開放" : `尚缺 ${health.external_test.blockers.length} 項`}</span></div><div className="space-y-2">{Object.entries(health.external_test.checks).map(([key, check]) => <div key={key} className="flex justify-between rounded-lg bg-background/70 px-3 py-2 text-sm"><span>{check.label}</span>{check.ok ? <span className="flex items-center gap-1 text-green-700"><CheckCircle2 className="h-4 w-4" />完成</span> : <span className="flex items-center gap-1 text-amber-700"><XCircle className="h-4 w-4" />阻擋</span>}</div>)}</div></section></div>}

    {slo && <section className="rounded-xl border bg-card p-5 shadow-sm"><div className="mb-4 flex items-center gap-2"><ShieldCheck className="h-5 w-5" /><h2 className="font-semibold">內部服務目標</h2><span className="ml-auto text-xs font-semibold">{slo.current.status === "healthy" ? "達標" : slo.current.status === "breached" ? "違反" : "證據不足"}</span></div><div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">{slo.current.metrics.map((metric) => <div key={metric.key} className={`rounded-lg border p-4 ${!metric.compliant ? "border-red-300 bg-red-50/40" : "bg-muted/20"}`}><p className="text-sm font-medium">{metric.label}</p><div className="mt-3 flex items-end justify-between"><span className="text-2xl font-semibold">{metricValue(metric)}</span><span className="text-xs text-muted-foreground">目標 {metricTarget(metric)} · {metric.window}</span></div>{metric.denominator !== null && <p className="mt-2 text-xs text-muted-foreground">樣本 {metric.numerator}/{metric.denominator} · 錯誤預算 {Math.round((metric.error_budget_remaining ?? 0) * 100)}%</p>}</div>)}</div></section>}

    <section className="overflow-hidden rounded-xl border bg-card shadow-sm"><div className="flex items-center gap-2 border-b px-5 py-4"><Siren className="h-5 w-5" /><h2 className="font-semibold">事故處置</h2><span className="ml-auto text-sm text-muted-foreground">進行中 {active.length}</span></div>{active.length === 0 ? <p className="p-5 text-sm text-muted-foreground">目前沒有待處理事故。</p> : <div className="divide-y">{active.map((incident) => <div key={incident.id} className="space-y-3 p-5"><div><span className={`rounded px-2 py-0.5 text-xs font-semibold ${incident.severity === "critical" ? "bg-red-100 text-red-700" : "bg-amber-100 text-amber-800"}`}>{incident.severity}</span><span className="ml-2 text-xs text-muted-foreground">{incident.status} · 發生 {incident.occurrence_count} 次</span><h3 className="mt-2 font-semibold">{incident.title}</h3><p className="mt-1 text-sm text-muted-foreground">{incident.summary}</p>{incident.notification_error && <p className="mt-1 text-xs text-red-600">告警：{incident.notification_error}</p>}</div><textarea className="min-h-20 w-full rounded-md border bg-background px-3 py-2 text-sm" placeholder="輸入處置依據（至少 10 個字元）" value={notes[incident.id] ?? ""} onChange={(event) => setNotes((current) => ({ ...current, [incident.id]: event.target.value }))} /><div className="flex gap-2"><Button variant="outline" size="sm" disabled={working === incident.id || incident.status === "acknowledged"} onClick={() => void act(incident, "acknowledge")}>確認處理</Button><Button size="sm" disabled={working === incident.id} onClick={() => void act(incident, "resolve")}>標記解決</Button></div></div>)}</div>}</section>

    {jobs && <section className="rounded-xl border bg-card p-5 shadow-sm"><div className="mb-4 flex items-center gap-2"><ServerCog className="h-5 w-5" /><h2 className="font-semibold">背景工作佇列</h2></div><div className="grid gap-3 sm:grid-cols-5">{[["等待", "pending"], ["重試", "retry"], ["處理中", "processing"], ["完成", "completed"], ["失敗", "failed"]].map(([label, key]) => <div key={key} className="rounded-lg border bg-muted/20 p-3"><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 text-xl font-semibold">{jobs.counts[key] ?? 0}</p></div>)}</div></section>}
    <section className="overflow-hidden rounded-xl border bg-card shadow-sm"><div className="border-b px-5 py-4"><h2 className="font-semibold">失敗工作</h2></div>{failedJobs.length === 0 ? <p className="p-5 text-sm text-muted-foreground">目前沒有失敗工作。</p> : <div className="divide-y">{failedJobs.map((job) => <div key={job.id} className="flex items-center gap-4 p-4 text-sm"><span className="font-mono text-xs">{job.job_type}</span><span className="min-w-0 flex-1 truncate text-red-600">{job.last_error || "未知錯誤"}</span><Button variant="outline" size="sm" onClick={() => void retryJob(job.id)} disabled={working === job.id}><RotateCcw className={`mr-1 h-3.5 w-3.5 ${working === job.id ? "animate-spin" : ""}`} />重試</Button></div>)}</div>}</section>
  </div>;
}
