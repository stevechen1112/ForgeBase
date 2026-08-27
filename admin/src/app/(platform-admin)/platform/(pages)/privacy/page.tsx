"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, RefreshCw, ShieldCheck, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type PrivacyOperation,
  type PrivacyRetentionInventory,
  type TenantSummary,
} from "@/lib/api/platform-admin";

const RETENTION_LABELS: Record<string, string> = {
  tracking_events: "逾期行為事件",
  tracking_sessions: "逾期瀏覽工作階段",
  network_observations: "逾期網路觀察",
  contact_candidates: "逾期未轉換窗口候選",
  journey_snapshots: "逾期旅程快照",
  inbound_reply_contents: "待遮蔽回覆內容",
};

const OPERATION_LABELS: Record<string, string> = {
  retention_run: "執行資料保留",
  visitor_export: "匯出匿名訪客資料",
  visitor_erasure: "清除匿名訪客資料",
};

export default function PrivacyOperationsPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : undefined;
  const [inventory, setInventory] = useState<PrivacyRetentionInventory | null>(null);
  const [operations, setOperations] = useState<PrivacyOperation[]>([]);
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantId, setTenantId] = useState("");
  const [visitorId, setVisitorId] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setError(null);
    try {
      const [nextInventory, nextOperations, nextTenants] = await Promise.all([
        platformAdminApi.privacyRetention(token),
        platformAdminApi.privacyOperations(token),
        platformAdminApi.tenants(token, { limit: 200 }),
      ]);
      setInventory(nextInventory);
      setOperations(nextOperations);
      setTenants(nextTenants);
      setTenantId((current) => current || nextTenants[0]?.id || "");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "讀取隱私作業狀態失敗");
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);

  async function runRetention() {
    if (!token || !window.confirm(`確定處理目前 ${inventory?.total_expired || 0} 筆逾期資料？`)) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await platformAdminApi.runPrivacyRetention(
        token,
        { confirm: true, reason: "例行執行已到期資料保留政策" },
        crypto.randomUUID(),
      );
      setNotice("資料保留作業完成；已保存不可變稽核紀錄。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "資料保留作業失敗"); }
    finally { setBusy(false); }
  }

  function validSubject() {
    if (!tenantId || !visitorId || reason.trim().length < 10) {
      setError("請選擇租戶、填入 Visitor UUID，並記錄至少 10 個字的申請理由。");
      return false;
    }
    return true;
  }

  async function exportVisitor() {
    if (!token || !validSubject()) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      const result = await platformAdminApi.exportVisitorPrivacyData(token, {
        tenant_id: tenantId, visitor_id: visitorId.trim(), reason: reason.trim(),
      });
      const blob = new Blob([JSON.stringify(result.export, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `forgebase-privacy-export-${result.operation_id}.json`;
      anchor.click();
      URL.revokeObjectURL(url);
      setNotice("資料已匯出到本機；伺服器只保存分類筆數與稽核紀錄，不保存匯出內容。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "資料匯出失敗"); }
    finally { setBusy(false); }
  }

  async function eraseVisitor() {
    if (!token || !validSubject()) return;
    if (!window.confirm("確定清除這名匿名訪客的追蹤與衍生證據？商務／法定紀錄會依政策保留。")) return;
    setBusy(true); setError(null); setNotice(null);
    try {
      await platformAdminApi.eraseVisitorPrivacyData(
        token,
        { tenant_id: tenantId, visitor_id: visitorId.trim(), reason: reason.trim() },
        crypto.randomUUID(),
      );
      setNotice("匿名追蹤與可刪除衍生證據已清除；Visitor 已撤回同意並去識別化。");
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "資料清除失敗"); }
    finally { setBusy(false); }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div><h1 className="text-2xl font-bold">隱私與資料保留</h1><p className="mt-1 max-w-3xl text-sm text-muted-foreground">集中檢視 TTL、執行到期清理，以及處理匿名訪客匯出／清除；所有高權限動作都留下不含原始識別碼的稽核紀錄。</p></div>
        <Button variant="outline" onClick={() => void load()} disabled={busy}><RefreshCw className={`mr-2 h-4 w-4 ${busy ? "animate-spin" : ""}`} />重新整理</Button>
      </div>

      {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}
      {notice && <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">{notice}</div>}

      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-3"><div><h2 className="text-sm font-semibold">到期資料佇列</h2><p className="mt-1 text-xs text-muted-foreground">行為資料全域保存 {inventory?.analytics_retention_days ?? "—"} 天；回覆正文到期後遮蔽內容、保留非 PII 事件鏈。</p></div><Button size="sm" onClick={runRetention} disabled={busy || !inventory || inventory.total_expired === 0}><Trash2 className="mr-2 h-4 w-4" />執行到期處理（{inventory?.total_expired ?? 0}）</Button></div>
        <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Object.entries(inventory?.expired || {}).map(([key, value]) => <div key={key} className={`rounded-lg border p-3 ${value ? "border-amber-300 bg-amber-50" : "border-emerald-200 bg-emerald-50"}`}><p className="text-xs text-muted-foreground">{RETENTION_LABELS[key] || key}</p><p className="mt-1 text-xl font-bold tabular-nums">{value}</p></div>)}</div>
        {inventory && Object.values(inventory.retained_business_evidence).some(Boolean) && <p className="mt-4 rounded-lg border border-blue-200 bg-blue-50 p-3 text-xs text-blue-800">另有 {Object.values(inventory.retained_business_evidence).reduce((sum, value) => sum + value, 0)} 筆逾期技術證據因已形成已轉換聯絡人或外聯商務紀錄而保留；不列入可刪除佇列。</p>}
      </div>

      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-primary" /><h2 className="text-sm font-semibold">匿名訪客資料請求</h2></div>
        <p className="mt-1 text-xs text-muted-foreground">先匯出供核對，再依正式申請清除。公司候選不等於個人身分；既有 RFQ、對話、已轉換聯絡人及必要寄送稽核不會被無差別刪除。</p>
        <div className="mt-5 grid gap-4 md:grid-cols-2">
          <label className="space-y-1.5"><Label>租戶</Label><select className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm" value={tenantId} onChange={(event) => setTenantId(event.target.value)}>{tenants.map((tenant) => <option key={tenant.id} value={tenant.id}>{tenant.name} · {tenant.slug}</option>)}</select></label>
          <label className="space-y-1.5"><Label>Visitor UUID</Label><Input value={visitorId} onChange={(event) => setVisitorId(event.target.value)} placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" /></label>
          <label className="space-y-1.5 md:col-span-2"><Label>申請來源／處理理由</Label><Input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={500} placeholder="例如：客服單 PRIV-2026-001，已核對第一方 cookie 識別碼" /></label>
        </div>
        <div className="mt-4 flex flex-wrap justify-end gap-2"><Button variant="outline" onClick={exportVisitor} disabled={busy}><Download className="mr-2 h-4 w-4" />匯出 JSON</Button><Button variant="destructive" onClick={eraseVisitor} disabled={busy}><Trash2 className="mr-2 h-4 w-4" />清除可刪除資料</Button></div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-card shadow-sm">
        <div className="border-b border-border px-5 py-3"><h2 className="text-sm font-semibold">最近隱私作業</h2></div>
        {operations.length === 0 ? <p className="p-5 text-sm text-muted-foreground">尚無隱私作業紀錄。</p> : <div className="divide-y divide-border">{operations.map((operation) => <div key={operation.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-3"><div><p className="text-sm font-medium">{OPERATION_LABELS[operation.operation_type] || operation.operation_type}</p><p className="mt-0.5 text-xs text-muted-foreground">{operation.tenant_id ? `Tenant ${operation.tenant_id.slice(0, 8)} · ` : ""}{operation.subject_hash_prefix ? `Subject ${operation.subject_hash_prefix}… · ` : ""}{operation.reason || "未記錄理由"}</p></div><time className="text-xs text-muted-foreground">{new Date(operation.completed_at).toLocaleString("zh-TW")}</time></div>)}</div>}
      </div>
    </div>
  );
}
