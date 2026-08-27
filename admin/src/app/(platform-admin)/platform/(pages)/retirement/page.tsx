"use client";

import { useCallback, useEffect, useState } from "react";
import { ArchiveX, RefreshCw, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type RetirementAuditReport,
  type RetirementCandidate,
} from "@/lib/api/platform-admin";

const STATUS_LABELS: Record<RetirementCandidate["status"], string> = {
  observing: "觀察中",
  retained: "決定保留",
  approved_removal: "已核准移除",
  removed: "已安全移除",
};

const BLOCKER_LABELS: Record<string, string> = {
  entry_not_disabled: "入口仍啟用",
  observation_window_incomplete: "觀察期尚未完成",
  usage_detected: "觀察期內仍有使用",
  configuration_detected: "仍有租戶啟用設定",
  retained_by_decision: "已有保留決策",
  telemetry_continuity_unverified: "尚未核驗觀察期間 telemetry 連續性",
  data_disposition_missing: "尚未記錄資料處置",
  rollback_revision_missing: "尚未指定可回復 revision",
  removal_plan_missing: "尚未連結退場變更計畫",
};

export default function RetirementAuditPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [report, setReport] = useState<RetirementAuditReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      setReport(await platformAdminApi.retirementAudit(token));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取退場稽核資料。");
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    void load();
  }, [load]);

  const decide = async (
    candidate: RetirementCandidate,
    status: "retained" | "approved_removal",
  ) => {
    const action = status === "retained" ? "保留" : "核准移除";
    const reason = window.prompt(
      `請輸入「${candidate.display_name}」決定${action}的證據與理由（至少 20 字）：`,
    );
    if (!reason || reason.trim().length < 20) return;
    const governance = status === "approved_removal" ? {
      telemetry_evidence_ref: window.prompt("Telemetry 連續性證據連結或工單編號：")?.trim(),
      data_disposition: window.prompt("資料處置（not_applicable／retained／exported／deleted）：")?.trim(),
      rollback_revision: window.prompt("已驗證可回復的 Git revision（7–40 位小寫 hex）：")?.trim(),
      removal_plan_ref: window.prompt("獨立退場變更計畫連結或工單編號：")?.trim(),
    } : {};
    if (status === "approved_removal" && Object.values(governance).some((value) => !value)) return;
    const allowedDispositions = ["not_applicable", "retained", "exported", "deleted"] as const;
    if (
      status === "approved_removal" &&
      !allowedDispositions.includes(governance.data_disposition as typeof allowedDispositions[number])
    ) {
      setError("資料處置值不合法。");
      return;
    }
    setSaving(candidate.candidate_key);
    setError("");
    try {
      await platformAdminApi.decideRetirementCandidate(token, candidate.candidate_key, {
        status,
        reason: reason.trim(),
        ...governance,
        data_disposition: governance.data_disposition as
          | "not_applicable"
          | "retained"
          | "exported"
          | "deleted"
          | undefined,
      });
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存退場決策。");
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold">
            <ArchiveX className="h-6 w-6" />
            功能退場稽核
          </h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            先關閉新入口並累積 30／60 天實際使用證據。只有觀察期完成、零使用且執行碼已停用的候選，才能核准下一個獨立刪除變更集。
          </p>
        </div>
        <Button variant="outline" onClick={() => void load()} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          重新整理
        </Button>
        {report && <Button variant="outline" onClick={() => {
          const blob = new Blob([JSON.stringify(report, null, 2)], { type: "application/json" });
          const url = URL.createObjectURL(blob);
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `forgebase-retirement-audit-${report.report_sha256.slice(0, 12)}.json`;
          anchor.click();
          URL.revokeObjectURL(url);
        }}>下載證據快照</Button>}
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="rounded-xl border border-amber-300/60 bg-amber-50 p-4 text-sm text-amber-950">
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
          <p>{report?.policy ?? "正在載入退場政策與觀察證據…"}</p>
        </div>
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        {report?.candidates.map((candidate) => (
          <article key={candidate.candidate_key} className="rounded-xl border bg-card p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="font-semibold">{candidate.display_name}</h2>
                <p className="mt-1 font-mono text-xs text-muted-foreground">
                  {candidate.candidate_key}
                </p>
              </div>
              <span className="rounded-full border px-2 py-1 text-xs font-medium">
                {STATUS_LABELS[candidate.status]}
              </span>
            </div>

            <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
              <div>
                <dt className="text-xs text-muted-foreground">程式狀態</dt>
                <dd className="mt-1 font-medium">{candidate.code_state}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">觀察進度</dt>
                <dd className="mt-1 font-medium">
                  {candidate.observed_days}／{candidate.required_observation_days} 天
                </dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">使用訊號</dt>
                <dd className="mt-1 font-medium tabular-nums">{candidate.recent_usage_count}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">涉及租戶（至少）</dt>
                <dd className="mt-1 font-medium tabular-nums">{candidate.tenant_count}</dd>
              </div>
            </dl>

            <p className="mt-4 rounded-lg bg-muted/50 p-3 text-xs text-muted-foreground">
              證據：{candidate.evidence.signal}；不保存 request payload 或 PII。
              {candidate.last_used_at
                ? ` 最後訊號：${new Date(candidate.last_used_at).toLocaleString("zh-TW")}`
                : " 尚無使用訊號。"}
            </p>

            {candidate.blockers.length > 0 && candidate.status !== "removed" && (
              <div className="mt-3 flex flex-wrap gap-2">
                {candidate.blockers.map((blocker) => (
                  <span key={blocker} className="rounded bg-amber-100 px-2 py-1 text-xs text-amber-800">
                    {BLOCKER_LABELS[blocker] ?? blocker}
                  </span>
                ))}
              </div>
            )}

            {candidate.status !== "removed" && (
              <div className="mt-4 flex flex-wrap gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={saving === candidate.candidate_key}
                  onClick={() => void decide(candidate, "retained")}
                >
                  決定保留
                </Button>
                <Button
                  size="sm"
                  disabled={!candidate.technical_removal_ready || saving === candidate.candidate_key}
                  onClick={() => void decide(candidate, "approved_removal")}
                >
                  核准移除
                </Button>
              </div>
            )}
          </article>
        ))}
      </div>

      {!loading && !report?.candidates.length && (
        <div className="rounded-xl border p-12 text-center text-sm text-muted-foreground">
          尚無退場候選。
        </div>
      )}
    </div>
  );
}
