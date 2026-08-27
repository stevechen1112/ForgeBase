"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, RefreshCw, Save, ShieldAlert, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type CompanyCandidate,
  type CompanyIdentificationMetrics,
  type GrowthAutomationPolicy,
  type TenantSummary,
} from "@/lib/api/platform-admin";

type EditablePolicy = Omit<GrowthAutomationPolicy, "tenant_id" | "updated_by" | "created_at" | "updated_at" | "persisted">;

const EMPTY_POLICY: EditablePolicy = {
  company_identification_mode: "off",
  provider_name: "mock",
  min_intent_score: 40,
  observation_retention_days: 30,
  daily_lookup_quota: 100,
  daily_provider_cost_limit: 10,
  medium_confidence_threshold: 0.7,
  high_confidence_threshold: 0.9,
  allowed_countries: [],
};

function count(values: Record<string, number> | undefined, key: string) {
  return values?.[key] ?? 0;
}

function confidenceVariant(band: CompanyCandidate["confidence_band"]) {
  if (band === "high") return "success" as const;
  if (band === "medium") return "warning" as const;
  return "secondary" as const;
}

export default function CompanyIdentificationPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [providers, setProviders] = useState<string[]>(["mock"]);
  const [tenantId, setTenantId] = useState("");
  const [policy, setPolicy] = useState<EditablePolicy>(EMPTY_POLICY);
  const [persisted, setPersisted] = useState(false);
  const [metrics, setMetrics] = useState<CompanyIdentificationMetrics | null>(null);
  const [candidates, setCandidates] = useState<CompanyCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [reviewingId, setReviewingId] = useState("");
  const [correctingId, setCorrectingId] = useState("");
  const [correctedName, setCorrectedName] = useState("");
  const [correctedDomain, setCorrectedDomain] = useState("");
  const [correctionNote, setCorrectionNote] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    void Promise.all([
      platformAdminApi.tenants(token, { is_active: true, limit: 200 }),
      platformAdminApi.companyIdentificationProviders(token),
    ]).then(([rows, providerResult]) => {
      setTenants(rows);
      setProviders(providerResult.data.filter((provider) => provider.healthy).map((provider) => provider.name));
      setTenantId((current) => current || rows[0]?.id || "");
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "無法讀取租戶或供應商。"));
  }, [token]);

  const load = useCallback(async () => {
    if (!token || !tenantId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [nextPolicy, nextMetrics, nextCandidates] = await Promise.all([
        platformAdminApi.growthAutomationPolicy(token, tenantId),
        platformAdminApi.companyIdentificationMetrics(token, tenantId),
        platformAdminApi.companyCandidates(token, tenantId, { limit: 100 }),
      ]);
      const { tenant_id: _tenantId, updated_by: _updatedBy, created_at: _createdAt, updated_at: _updatedAt, persisted: nextPersisted, ...editable } = nextPolicy;
      void _tenantId; void _updatedBy; void _createdAt; void _updatedAt;
      setPolicy(editable);
      setPersisted(nextPersisted);
      setMetrics(nextMetrics);
      setCandidates(nextCandidates.data);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法讀取公司推測資料。" );
    } finally {
      setLoading(false);
    }
  }, [tenantId, token]);

  useEffect(() => { void load(); }, [load]);

  const selectedTenant = useMemo(() => tenants.find((tenant) => tenant.id === tenantId), [tenantId, tenants]);

  async function savePolicy() {
    if (!tenantId) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const saved = await platformAdminApi.updateGrowthAutomationPolicy(token, tenantId, policy);
      setPersisted(saved.persisted);
      setMessage(saved.company_identification_mode === "shadow" ? "Shadow Mode 已儲存；只觀察與產生候選，不會聯絡任何人。" : "公司推測已關閉。" );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存策略。" );
    } finally {
      setSaving(false);
    }
  }

  async function review(candidate: CompanyCandidate, decision: "confirm" | "reject") {
    setReviewingId(candidate.id); setError(""); setMessage("");
    try {
      let note: string | undefined;
      let reason_code: string | undefined;
      if (decision === "reject") {
        note = window.prompt("請輸入排除原因（會保存於品質稽核紀錄）")?.trim();
        if (!note) return;
        reason_code = "manual_reject";
      }
      await platformAdminApi.reviewCompanyCandidate(token, candidate.id, { decision, reason_code, note });
      setMessage(decision === "confirm" ? `已確認 ${candidate.company_name}。` : `已排除 ${candidate.company_name}。`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存審核。" );
    } finally {
      setReviewingId("");
    }
  }

  function beginCorrection(candidate: CompanyCandidate) {
    setCorrectingId(candidate.id);
    setCorrectedName(candidate.company_name);
    setCorrectedDomain(candidate.domain);
    setCorrectionNote("");
  }

  async function saveCorrection() {
    const candidate = candidates.find((row) => row.id === correctingId);
    if (!candidate || !correctedName.trim() || !correctedDomain.trim()) return;
    setReviewingId(candidate.id); setError(""); setMessage("");
    try {
      await platformAdminApi.reviewCompanyCandidate(token, candidate.id, {
        decision: "correct",
        reason_code: "manual_correction",
        note: correctionNote.trim() || undefined,
        corrected_company_name: correctedName.trim(),
        corrected_domain: correctedDomain.trim().toLowerCase(),
      });
      setCorrectingId("");
      setMessage(`已修正並確認 ${correctedName.trim()}。`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存修正。" );
    } finally {
      setReviewingId("");
    }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-bold">公司推測 Shadow Mode</h1>
        <p className="mt-1 max-w-3xl text-sm text-muted-foreground">根據合規的匿名網路觀察推測可能造訪的公司。這不是個人身分辨識；目前僅允許關閉或影子觀察，不會自動補全聯絡人或寄信。</p>
      </div>
      <Button variant="outline" onClick={() => void load()} disabled={loading || !tenantId}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button>
    </div>

    <div className="flex max-w-xl items-center gap-3">
      <Label className="shrink-0">租戶</Label>
      <Select value={tenantId} onValueChange={setTenantId}>
        <SelectTrigger><SelectValue placeholder="選擇租戶" /></SelectTrigger>
        <SelectContent>{tenants.map((tenant) => <SelectItem key={tenant.id} value={tenant.id}>{tenant.name}（{tenant.slug}）</SelectItem>)}</SelectContent>
      </Select>
    </div>

    {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}
    {message && <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</div>}
    {!loading && tenants.length === 0 && <div className="rounded-lg border p-6 text-sm text-muted-foreground">目前沒有可管理的啟用租戶。</div>}

    {tenantId && <>
      <Card>
        <CardHeader className="flex-row items-center justify-between gap-4"><div><CardTitle>觀察策略</CardTitle><p className="mt-1 text-sm text-muted-foreground">{selectedTenant?.name} · {persisted ? "已建立租戶策略" : "使用安全預設值，尚未寫入"}</p></div><Badge variant={policy.company_identification_mode === "shadow" ? "info" : "secondary"}>{policy.company_identification_mode === "shadow" ? "SHADOW" : "OFF"}</Badge></CardHeader>
        <CardContent className="grid gap-5 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-2"><Label>模式</Label><Select value={policy.company_identification_mode} onValueChange={(value: "off" | "shadow") => setPolicy({ ...policy, company_identification_mode: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="off">關閉</SelectItem><SelectItem value="shadow">Shadow（只觀察）</SelectItem></SelectContent></Select></div>
          <div className="space-y-2"><Label>公司資料供應商</Label><Select value={policy.provider_name} onValueChange={(value) => setPolicy({ ...policy, provider_name: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{providers.map((provider) => <SelectItem key={provider} value={provider}>{provider === "mock" ? "Mock（不連外）" : provider}</SelectItem>)}</SelectContent></Select></div>
          <div className="space-y-2"><Label>最低意圖分數</Label><Input type="number" min={0} max={1000} value={policy.min_intent_score} onChange={(event) => setPolicy({ ...policy, min_intent_score: Number(event.target.value) })} /></div>
          <div className="space-y-2"><Label>每日查詢上限</Label><Input type="number" min={0} max={100000} value={policy.daily_lookup_quota} onChange={(event) => setPolicy({ ...policy, daily_lookup_quota: Number(event.target.value) })} /></div>
          <div className="space-y-2"><Label>每日供應商成本上限</Label><Input type="number" min={0} max={1000000} step={0.01} value={policy.daily_provider_cost_limit} onChange={(event) => setPolicy({ ...policy, daily_provider_cost_limit: Number(event.target.value) })} /></div>
          <div className="space-y-2"><Label>觀察保留天數</Label><Input type="number" min={1} max={365} value={policy.observation_retention_days} onChange={(event) => setPolicy({ ...policy, observation_retention_days: Number(event.target.value) })} /></div>
          <div className="space-y-2"><Label>中信心門檻</Label><Input type="number" min={0} max={1} step={0.01} value={policy.medium_confidence_threshold} onChange={(event) => setPolicy({ ...policy, medium_confidence_threshold: Number(event.target.value) })} /></div>
          <div className="space-y-2"><Label>高信心門檻</Label><Input type="number" min={0} max={1} step={0.01} value={policy.high_confidence_threshold} onChange={(event) => setPolicy({ ...policy, high_confidence_threshold: Number(event.target.value) })} /></div>
          <div className="space-y-2 md:col-span-2"><Label>允許國家（ISO 代碼，以逗號分隔）</Label><Input placeholder="TW, JP, US；空白代表不限制" value={policy.allowed_countries.join(", ")} onChange={(event) => setPolicy({ ...policy, allowed_countries: event.target.value.split(",").map((value) => value.trim().toUpperCase()).filter(Boolean) })} /></div>
          <div className="md:col-span-2 xl:col-span-4"><Button onClick={() => void savePolicy()} disabled={saving}><Save className="mr-2 h-4 w-4" />{saving ? "儲存中…" : "儲存策略"}</Button></div>
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card><CardHeader><CardTitle className="text-sm font-medium">合規觀察</CardTitle></CardHeader><CardContent className="text-3xl font-bold">{count(metrics?.observations, "eligible").toLocaleString()}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm font-medium">待審候選</CardTitle></CardHeader><CardContent className="text-3xl font-bold">{(count(metrics?.candidates, "shadow") + count(metrics?.candidates, "candidate") + count(metrics?.candidates, "conflict")).toLocaleString()}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm font-medium">已確認公司</CardTitle></CardHeader><CardContent className="text-3xl font-bold">{count(metrics?.candidates, "confirmed").toLocaleString()}</CardContent></Card>
        <Card><CardHeader><CardTitle className="text-sm font-medium">高信心精準率 Gate</CardTitle></CardHeader><CardContent><div className="flex items-center gap-2 text-2xl font-bold">{metrics?.precision_gate_passed ? <CheckCircle2 className="text-emerald-600" /> : <ShieldAlert className="text-amber-600" />}{metrics?.high_confidence_precision == null ? "樣本不足" : `${(metrics.high_confidence_precision * 100).toFixed(1)}%`}</div><p className="mt-2 text-xs text-muted-foreground">需達 90%，且仍須人工審核後才能推進下一模式。</p></CardContent></Card>
      </div>

      <Card>
        <CardHeader><CardTitle>Shadow 品質與成本</CardTitle><p className="text-sm text-muted-foreground">Match rate 與人工 precision 分開呈現，避免以降低門檻製造表面覆蓋率。</p></CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
          <div><p className="text-xs text-muted-foreground">Match rate</p><p className="text-xl font-semibold">{metrics?.match_rate == null ? "—" : `${(metrics.match_rate * 100).toFixed(1)}%`}</p></div>
          <div><p className="text-xs text-muted-foreground">高信心占比</p><p className="text-xl font-semibold">{metrics?.high_confidence_rate == null ? "—" : `${(metrics.high_confidence_rate * 100).toFixed(1)}%`}</p></div>
          <div><p className="text-xs text-muted-foreground">Unknown</p><p className="text-xl font-semibold">{metrics?.unknown_count.toLocaleString() ?? "—"}</p></div>
          <div><p className="text-xs text-muted-foreground">Conflict</p><p className="text-xl font-semibold">{metrics?.conflict_count.toLocaleString() ?? "—"}</p></div>
          <div><p className="text-xs text-muted-foreground">查詢數</p><p className="text-xl font-semibold">{metrics?.lookup_attempts.toLocaleString() ?? "—"}</p></div>
          <div><p className="text-xs text-muted-foreground">預估成本</p><p className="text-xl font-semibold">{metrics ? metrics.total_estimated_cost.toFixed(2) : "—"}</p></div>
          <div className="md:col-span-3 xl:col-span-6 overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="py-2">Provider</th><th>狀態</th><th>請求</th><th>平均延遲</th><th>Units</th><th>成本</th></tr></thead><tbody>{metrics?.provider_usage.map((usage) => <tr key={`${usage.provider}:${usage.status}`} className="border-b last:border-0"><td className="py-2">{usage.provider}</td><td>{usage.status}</td><td>{usage.requests}</td><td>{usage.average_latency_ms.toFixed(0)} ms</td><td>{usage.units}</td><td>{usage.estimated_cost.toFixed(4)}</td></tr>)}</tbody></table></div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>推測公司候選</CardTitle><p className="text-sm text-muted-foreground">顯示供應商推測與經清洗的證據，不顯示原始 IP。</p></CardHeader>
        <CardContent>
          {correctingId && <div className="mb-5 grid gap-3 rounded-lg border bg-muted/30 p-4 md:grid-cols-2"><div className="space-y-2"><Label>修正公司名稱</Label><Input value={correctedName} onChange={(event) => setCorrectedName(event.target.value)} /></div><div className="space-y-2"><Label>修正公司網域</Label><Input value={correctedDomain} onChange={(event) => setCorrectedDomain(event.target.value)} /></div><div className="space-y-2 md:col-span-2"><Label>修正說明（選填）</Label><Input value={correctionNote} onChange={(event) => setCorrectionNote(event.target.value)} /></div><div className="flex gap-2 md:col-span-2"><Button onClick={() => void saveCorrection()} disabled={reviewingId === correctingId}>儲存修正</Button><Button variant="outline" onClick={() => setCorrectingId("")}>取消</Button></div></div>}
          {candidates.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">目前沒有候選公司。</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">公司</th><th className="p-3">信心</th><th className="p-3">方法／來源</th><th className="p-3">狀態</th><th className="p-3 text-right">人工審核</th></tr></thead><tbody>{candidates.map((candidate) => {
            const disabled = reviewingId === candidate.id || candidate.status === "expired";
            return <tr key={candidate.id} className="border-b last:border-0"><td className="p-3"><div className="font-medium">{candidate.company_name}</div><div className="text-xs text-muted-foreground">{candidate.domain}</div></td><td className="p-3"><Badge variant={confidenceVariant(candidate.confidence_band)}>{candidate.confidence_band} · {(candidate.confidence * 100).toFixed(0)}%</Badge></td><td className="p-3"><div>{candidate.match_method}</div><div className="text-xs text-muted-foreground">{candidate.provider}</div></td><td className="p-3"><Badge variant={candidate.status === "confirmed" ? "success" : candidate.status === "rejected" ? "destructive" : "outline"}>{candidate.status}</Badge></td><td className="p-3"><div className="flex justify-end gap-2"><Button size="sm" variant="outline" disabled={disabled} onClick={() => beginCorrection(candidate)}>修正</Button><Button size="sm" variant="outline" disabled={disabled} onClick={() => void review(candidate, "reject")}><XCircle className="mr-1 h-4 w-4" />排除</Button><Button size="sm" disabled={disabled} onClick={() => void review(candidate, "confirm")}><CheckCircle2 className="mr-1 h-4 w-4" />確認</Button></div></td></tr>;
          })}</tbody></table></div>}
        </CardContent>
      </Card>
    </>}
  </div>;
}
