"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { agentosApi, type RunView, type Approval } from "@/lib/api/agentos";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCcw, Bot, CheckCircle2, XCircle, Clock, ChevronDown, ChevronUp, Loader2 } from "lucide-react";

const RUN_STATUS_CONFIG: Record<string, { label: string; cls: string }> = {
  created:          { label: "已建立",   cls: "bg-muted text-muted-foreground" },
  running:          { label: "執行中",   cls: "bg-blue-100 text-blue-700" },
  waiting_approval: { label: "等待審批", cls: "bg-amber-100 text-amber-700" },
  completed:        { label: "已完成",   cls: "bg-green-100 text-green-700" },
  failed:           { label: "失敗",     cls: "bg-red-100 text-red-700" },
  canceled:         { label: "已取消",   cls: "bg-muted text-muted-foreground" },
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "剛才";
  if (mins < 60) return `${mins} 分鐘前`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} 小時前`;
  return `${Math.floor(hrs / 24)} 天前`;
}

function ApprovalRow({
  approval,
  actorId,
  onDecide,
}: {
  approval: Approval;
  actorId: string;
  onDecide: (approvalId: string, decision: "approved" | "rejected") => Promise<void>;
}) {
  const [deciding, setDeciding] = useState<"approved" | "rejected" | null>(null);

  const handle = async (decision: "approved" | "rejected") => {
    setDeciding(decision);
    await onDecide(approval.id, decision);
    setDeciding(null);
  };

  const isPending = approval.decision === "pending";

  return (
    <div className="rounded-lg border bg-amber-50/50 dark:bg-amber-950/10 px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-foreground">{approval.checkpoint}</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Step: <code className="font-mono text-xs bg-muted px-1 rounded">{approval.step_id.slice(0, 8)}…</code>
            {" · "}到期：{approval.expires_at ? new Date(approval.expires_at).toLocaleString("zh-TW") : "無"}
          </p>
          {!isPending && (
            <p className="text-xs mt-1 font-medium text-muted-foreground">
              {approval.decision === "approved" && <span className="text-green-600">✓ 已核准</span>}
              {approval.decision === "rejected" && <span className="text-red-600">✗ 已拒絕</span>}
              {" by "}{approval.actor_id ?? "system"}
            </p>
          )}
        </div>
        {isPending && (
          <div className="flex shrink-0 gap-2">
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-xs border-green-300 text-green-700 hover:bg-green-50"
              disabled={deciding !== null}
              onClick={() => handle("approved")}
            >
              {deciding === "approved" ? <Loader2 className="h-3 w-3 animate-spin" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
              核准
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 gap-1 text-xs border-red-300 text-red-700 hover:bg-red-50"
              disabled={deciding !== null}
              onClick={() => handle("rejected")}
            >
              {deciding === "rejected" ? <Loader2 className="h-3 w-3 animate-spin" /> : <XCircle className="h-3.5 w-3.5" />}
              拒絕
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

function RunCard({
  view,
  actorId,
  onDecide,
}: {
  view: RunView;
  actorId: string;
  onDecide: (approvalId: string, decision: "approved" | "rejected") => Promise<void>;
}) {
  const [expanded, setExpanded] = useState(view.run.status === "waiting_approval");
  const cfg = RUN_STATUS_CONFIG[view.run.status] ?? { label: view.run.status, cls: "bg-muted text-muted-foreground" };
  const pendingApprovals = view.approvals.filter((a) => a.decision === "pending");

  return (
    <Card className={view.run.status === "waiting_approval" ? "border-amber-300 dark:border-amber-700" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            <Bot className="h-4 w-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="text-sm font-mono font-medium text-foreground truncate">{view.run.id}</p>
              <p className="text-xs text-muted-foreground">{relativeTime(view.run.started_at)}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${cfg.cls}`}>
              {view.run.status === "waiting_approval" && <Clock className="mr-1 h-3 w-3 animate-pulse" />}
              {cfg.label}
            </span>
            {pendingApprovals.length > 0 && (
              <Badge variant="destructive" className="text-[10px]">
                {pendingApprovals.length} 待審批
              </Badge>
            )}
            <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setExpanded((v) => !v)}>
              {expanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
            </Button>
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="pt-0 space-y-3">
          <div className="text-xs text-muted-foreground space-y-0.5">
            <p>Task ID: <code className="font-mono bg-muted px-1 rounded">{view.run.task_id}</code></p>
            <p>狀態摘要: {view.run_state.summary}</p>
            {view.run_state.last_error && (
              <p className="text-red-600">錯誤: {view.run_state.last_error}</p>
            )}
          </div>

          {view.approvals.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">審批項目</p>
              {view.approvals.map((a) => (
                <ApprovalRow key={a.id} approval={a} actorId={actorId} onDecide={onDecide} />
              ))}
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}

export default function AgentRunsPage() {
  const { state } = useAuth();
  const user = state.status === "authenticated" ? state.user : null;
  const actorId = user?.email ?? "admin";

  const [runs, setRuns] = useState<RunView[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const status = statusFilter === "all" ? undefined : statusFilter;
      const data = await agentosApi.listRuns(status as Parameters<typeof agentosApi.listRuns>[0]);
      setRuns(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "載入失敗");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => { load(); }, [load]);

  const handleDecide = useCallback(async (approvalId: string, decision: "approved" | "rejected") => {
    await agentosApi.decideApproval(approvalId, decision, actorId);
    await load();
  }, [actorId, load]);

  const waitingCount = runs.filter((r) => r.run.status === "waiting_approval").length;
  const runningCount = runs.filter((r) => r.run.status === "running").length;
  const failedCount = runs.filter((r) => r.run.status === "failed").length;

  const STATUS_TABS = [
    { value: "all",              label: "全部" },
    { value: "waiting_approval", label: "等待審批" },
    { value: "running",          label: "執行中" },
    { value: "completed",        label: "已完成" },
    { value: "failed",           label: "失敗" },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Bot className="h-6 w-6 text-muted-foreground" />
            Agent 任務佇列
          </h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            監控 AgentOS 工作流程執行狀態，審批待確認項目
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading} className="gap-1.5">
          <RefreshCcw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          重新整理
        </Button>
      </div>

      {/* Summary chips */}
      <div className="flex flex-wrap gap-3">
        {waitingCount > 0 && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 dark:border-amber-800 dark:bg-amber-950/20">
            <p className="text-xs text-amber-700 dark:text-amber-400">等待審批</p>
            <p className="text-xl font-bold text-amber-800 dark:text-amber-300">{waitingCount}</p>
          </div>
        )}
        {runningCount > 0 && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2 dark:border-blue-800 dark:bg-blue-950/20">
            <p className="text-xs text-blue-700 dark:text-blue-400">執行中</p>
            <p className="text-xl font-bold text-blue-800 dark:text-blue-300">{runningCount}</p>
          </div>
        )}
        {failedCount > 0 && (
          <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 dark:border-red-800 dark:bg-red-950/20">
            <p className="text-xs text-red-700 dark:text-red-400">失敗</p>
            <p className="text-xl font-bold text-red-800 dark:text-red-300">{failedCount}</p>
          </div>
        )}
      </div>

      {/* Status filter tabs */}
      <div className="flex flex-wrap gap-1.5">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setStatusFilter(tab.value)}
            className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
              statusFilter === tab.value
                ? "bg-foreground text-background"
                : "border border-input bg-background text-muted-foreground hover:text-foreground"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>AgentOS 連線失敗：{error}。請確認 AgentOS 服務是否啟動。</AlertDescription>
        </Alert>
      )}

      {/* Runs list */}
      {loading && runs.length === 0 ? (
        <div className="py-12 text-center text-sm text-muted-foreground">載入中…</div>
      ) : runs.length === 0 ? (
        <div className="rounded-xl border border-dashed py-16 text-center">
          <Bot className="mx-auto h-8 w-8 text-muted-foreground/40" />
          <p className="mt-3 text-sm text-muted-foreground">
            {statusFilter === "all" ? "目前沒有任何 Agent 任務紀錄" : `沒有「${STATUS_TABS.find(t => t.value === statusFilter)?.label}」的任務`}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {runs.map((view) => (
            <RunCard key={view.run.id} view={view} actorId={actorId} onDecide={handleDecide} />
          ))}
        </div>
      )}
    </div>
  );
}
