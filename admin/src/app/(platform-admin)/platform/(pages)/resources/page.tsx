"use client";

import { useCallback, useEffect, useState } from "react";
import { CheckCircle2, RefreshCw, XCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import { platformAdminApi, type PlatformResourceStatus } from "@/lib/api/platform-admin";

function Status({ ok, yes = "已設定", no = "尚未設定" }: { ok: boolean; yes?: string; no?: string }) {
  return ok ? <span className="inline-flex items-center gap-1 text-emerald-700"><CheckCircle2 className="h-4 w-4" />{yes}</span> : <span className="inline-flex items-center gap-1 text-amber-700"><XCircle className="h-4 w-4" />{no}</span>;
}

function ResourceCard({ title, children }: { title: string; children: React.ReactNode }) {
  return <section className="rounded-xl border bg-card p-5 shadow-sm"><h2 className="font-semibold">{title}</h2><div className="mt-4 space-y-3 text-sm">{children}</div></section>;
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="flex items-center justify-between gap-4"><span className="text-muted-foreground">{label}</span><span className="text-right">{children}</span></div>;
}

export default function PlatformResourcesPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [data, setData] = useState<PlatformResourceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true); setError("");
    try { setData(await platformAdminApi.resourceStatus(token)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "無法讀取外部服務狀態。"); }
    finally { setLoading(false); }
  }, [token]);
  useEffect(() => { void load(); }, [load]);
  const formatBytes = (value = 0) => value < 1024 * 1024 ? `${value.toLocaleString()} B` : `${(value / 1024 / 1024).toFixed(1)} MB`;

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div><h1 className="text-2xl font-bold">外部服務與資料</h1><p className="mt-1 text-sm text-muted-foreground">只顯示可安全確認的設定與執行證據；平台不會顯示 API Key、Token 或密碼。</p></div>
      <Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
    </div>
    {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}
    {data && <>
      <div className={`rounded-xl border p-5 ${data.external_test.ready ? "border-emerald-300 bg-emerald-50/40" : "border-amber-300 bg-amber-50/50"}`}>
        <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">正式外部測試 Gate</h2><p className="mt-1 text-sm text-muted-foreground">所有項目通過後，才可宣告能承接不特定外部測試流量。</p></div><Status ok={data.external_test.ready} yes="可開放" no={`尚缺 ${data.external_test.blockers.length} 項`} /></div>
        <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">{Object.entries(data.external_test.checks).map(([key, check]) => <div key={key} className="flex items-center justify-between rounded-lg bg-background/70 px-3 py-2 text-sm"><span>{check.label}</span><Status ok={check.ok} yes="完成" no="待設定" /></div>)}</div>
      </div>
      <div className="grid gap-5 lg:grid-cols-2 xl:grid-cols-3">
        <ResourceCard title="公開表單"><Row label="簽章 challenge"><Status ok={data.forms.signed_challenge_required} /></Row><Row label="Turnstile"><Status ok={data.forms.turnstile_configured} /></Row><Row label="允許網域"><Status ok={data.forms.allowed_hostnames_configured} /></Row></ResourceCard>
        <ResourceCard title="Email 與內部通知"><Row label={`${data.email.provider} API`}><Status ok={data.email.provider_configured} /></Row><Row label="Webhook 驗簽"><Status ok={data.email.webhook_configured} /></Row><Row label="內部收件 allowlist"><Status ok={data.email.internal_allowlist_configured} /></Row><Row label="外部寄信"><Status ok={!data.email.external_delivery_enabled} yes="維持關閉" no="已開啟" /></Row><Row label="目前模式">{data.email.dry_run ? "Dry run" : "正式投遞"}</Row></ResourceCard>
        <ResourceCard title="素材儲存"><Row label="R2 設定"><Status ok={data.storage.r2_configured} /></Row><Row label="已登錄素材">{data.storage.asset_count.toLocaleString()} 件</Row><Row label="使用空間">{formatBytes(data.storage.asset_bytes)}</Row><Row label="有素材的租戶">{data.storage.tenants_with_assets}</Row></ResourceCard>
        <ResourceCard title="異地備份"><Row label="備份儲存設定"><Status ok={data.backups.offsite_configured} /></Row><Row label="證據狀態"><Status ok={data.backups.evidence_status === "verified"} yes="備份與還原皆已驗證" no={data.backups.evidence_status === "backup_only" ? "已有備份，待還原演練" : "尚未記錄"} /></Row><Row label="最後備份證據">{data.backups.last_backup_at ? new Date(data.backups.last_backup_at).toLocaleString("zh-TW") : "尚未記錄"}</Row><Row label="還原演練">{data.backups.last_restore_drill_at ? new Date(data.backups.last_restore_drill_at).toLocaleString("zh-TW") : "尚未記錄"}</Row></ResourceCard>
        <ResourceCard title="告警與站外監控"><Row label="主動告警"><Status ok={data.monitoring.incident_alert_configured} /></Row><Row label="站外監控"><Status ok={data.monitoring.external_monitor_configured} /></Row><Row label="監控名稱">{data.monitoring.external_monitor_name || "尚未設定"}</Row></ResourceCard>
      </div>
    </>}
  </div>;
}
