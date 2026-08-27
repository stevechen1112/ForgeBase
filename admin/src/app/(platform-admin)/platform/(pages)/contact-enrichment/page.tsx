"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { CheckCircle2, ContactRound, RefreshCw, Save, ShieldBan, UserPlus, XCircle } from "lucide-react";
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
  type ContactCandidate,
  type ContactEnrichmentMetrics,
  type ContactPersonaPolicy,
  type TenantSummary,
} from "@/lib/api/platform-admin";

type EditablePolicy = Omit<ContactPersonaPolicy, "tenant_id" | "updated_by" | "updated_at" | "persisted">;

const EMPTY_POLICY: EditablePolicy = {
  mode: "off",
  contact_provider_name: "mock",
  verification_provider_name: "mock",
  target_departments: ["procurement", "engineering"],
  target_titles: ["procurement", "purchasing", "engineering"],
  target_seniorities: ["manager", "director", "vp"],
  target_locations: [],
  excluded_title_terms: ["intern", "student"],
  min_relevance_score: 60,
  candidate_retention_days: 90,
  max_candidates_per_company: 5,
  daily_lookup_quota: 25,
  daily_provider_cost_limit: 5,
};

function csv(values: string[]) { return values.join(", "); }
function parseCsv(value: string) { return value.split(",").map((item) => item.trim()).filter(Boolean); }

function verificationVariant(status: ContactCandidate["verification_status"]) {
  if (status === "verified") return "success" as const;
  if (status === "invalid") return "destructive" as const;
  if (status === "risky" || status === "catch_all") return "warning" as const;
  return "secondary" as const;
}

export default function ContactEnrichmentPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantId, setTenantId] = useState("");
  const [policy, setPolicy] = useState<EditablePolicy>(EMPTY_POLICY);
  const [companies, setCompanies] = useState<CompanyCandidate[]>([]);
  const [candidates, setCandidates] = useState<ContactCandidate[]>([]);
  const [metrics, setMetrics] = useState<ContactEnrichmentMetrics | null>(null);
  const [contactProviders, setContactProviders] = useState<string[]>([]);
  const [verificationProviders, setVerificationProviders] = useState<string[]>([]);
  const [busy, setBusy] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) return;
    void Promise.all([
      platformAdminApi.tenants(token, { is_active: true, limit: 200 }),
      platformAdminApi.contactEnrichmentProviders(token),
    ]).then(([rows, providers]) => {
      setTenants(rows);
      setTenantId((current) => current || rows[0]?.id || "");
      setContactProviders(providers.contact.filter((item) => item.healthy).map((item) => item.name));
      setVerificationProviders(providers.verification.filter((item) => item.healthy).map((item) => item.name));
    }).catch((cause) => setError(cause instanceof Error ? cause.message : "無法載入租戶與供應商。"));
  }, [token]);

  const load = useCallback(async () => {
    if (!token || !tenantId) { setLoading(false); return; }
    setLoading(true); setError("");
    try {
      const [nextPolicy, companyRows, candidateRows, nextMetrics] = await Promise.all([
        platformAdminApi.contactPersonaPolicy(token, tenantId),
        platformAdminApi.companyCandidates(token, tenantId, { status: "confirmed", limit: 100 }),
        platformAdminApi.contactCandidates(token, tenantId, { limit: 100 }),
        platformAdminApi.contactEnrichmentMetrics(token, tenantId),
      ]);
      const { tenant_id: _tenantId, updated_by: _updatedBy, updated_at: _updatedAt, persisted: _persisted, ...editable } = nextPolicy;
      void _tenantId; void _updatedBy; void _updatedAt; void _persisted;
      setPolicy(editable);
      setCompanies(companyRows.data);
      setCandidates(candidateRows.data);
      setMetrics(nextMetrics);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法載入聯絡窗口候選。" );
    } finally { setLoading(false); }
  }, [tenantId, token]);

  useEffect(() => { void load(); }, [load]);
  const selectedTenant = useMemo(() => tenants.find((row) => row.id === tenantId), [tenantId, tenants]);

  async function savePolicy() {
    setBusy("policy"); setError(""); setMessage("");
    try {
      await platformAdminApi.updateContactPersonaPolicy(token, tenantId, policy);
      setMessage(policy.mode === "review_only" ? "Review Only 已儲存；可產生候選，但不會寄信或自動轉成聯絡人。" : "聯絡窗口補全已關閉。" );
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法儲存 persona 策略。" ); }
    finally { setBusy(""); }
  }

  async function enqueue(company: CompanyCandidate) {
    setBusy(company.id); setError(""); setMessage("");
    try {
      await platformAdminApi.enqueueContactEnrichment(token, company.id);
      setMessage(`已排程搜尋 ${company.company_name} 的公司相關商務窗口。`);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法排程補全。" ); }
    finally { setBusy(""); }
  }

  async function review(candidate: ContactCandidate, decision: "approve" | "reject" | "do_not_contact") {
    let reason_code: string | undefined;
    let note: string | undefined;
    if (decision !== "approve") {
      note = window.prompt(decision === "reject" ? "請輸入拒絕原因" : "請輸入禁止聯絡原因")?.trim();
      if (!note) return;
      reason_code = decision === "reject" ? "manual_reject" : "manual_do_not_contact";
    }
    setBusy(candidate.id); setError(""); setMessage("");
    try {
      await platformAdminApi.reviewContactCandidate(token, candidate.id, { decision, reason_code, note });
      setMessage(`已更新 ${candidate.full_name} 的人工決策。`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法儲存審核。" ); }
    finally { setBusy(""); }
  }

  async function convert(candidate: ContactCandidate) {
    if (!window.confirm("轉成正式 Contact？此動作不會把此人綁定為原匿名訪客。")) return;
    setBusy(candidate.id); setError(""); setMessage("");
    try {
      const result = await platformAdminApi.convertContactCandidate(token, candidate.id);
      setMessage(`已人工轉成正式聯絡人（${result.contact_id}），未建立 visitor 身分連結。`);
      await load();
    } catch (cause) { setError(cause instanceof Error ? cause.message : "無法轉成正式聯絡人。" ); }
    finally { setBusy(""); }
  }

  return <div className="space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4"><div><h1 className="text-2xl font-bold">公司相關聯絡窗口候選</h1><p className="mt-1 max-w-3xl text-sm text-muted-foreground">只從已人工確認的公司與限定 persona 搜尋公開商務窗口。候選不代表匿名訪客本人；信箱只顯示遮罩，核准也不會寄信。</p></div><Button variant="outline" onClick={() => void load()} disabled={loading}><RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理</Button></div>
    <div className="flex max-w-xl items-center gap-3"><Label className="shrink-0">租戶</Label><Select value={tenantId} onValueChange={setTenantId}><SelectTrigger><SelectValue placeholder="選擇租戶" /></SelectTrigger><SelectContent>{tenants.map((tenant) => <SelectItem key={tenant.id} value={tenant.id}>{tenant.name}（{tenant.slug}）</SelectItem>)}</SelectContent></Select></div>
    {error && <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}
    {message && <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">{message}</div>}
    {tenantId && <>
      <Card><CardHeader className="flex-row items-center justify-between"><div><CardTitle>Persona 與成本護欄</CardTitle><p className="mt-1 text-sm text-muted-foreground">{selectedTenant?.name} · 至少指定部門或職稱，禁止無限制抓取。</p></div><Badge variant={policy.mode === "review_only" ? "info" : "secondary"}>{policy.mode === "review_only" ? "REVIEW ONLY" : "OFF"}</Badge></CardHeader><CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <div className="space-y-2"><Label>模式</Label><Select value={policy.mode} onValueChange={(mode: "off" | "review_only") => setPolicy({ ...policy, mode })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="off">關閉</SelectItem><SelectItem value="review_only">只產生候選與人工審核</SelectItem></SelectContent></Select></div>
        <div className="space-y-2"><Label>窗口供應商</Label><Select value={policy.contact_provider_name} onValueChange={(value) => setPolicy({ ...policy, contact_provider_name: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{contactProviders.map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}</SelectContent></Select></div>
        <div className="space-y-2"><Label>信箱驗證供應商</Label><Select value={policy.verification_provider_name} onValueChange={(value) => setPolicy({ ...policy, verification_provider_name: value })}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{verificationProviders.map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}</SelectContent></Select></div>
        <div className="space-y-2"><Label>最低相關度</Label><Input type="number" min={0} max={100} value={policy.min_relevance_score} onChange={(event) => setPolicy({ ...policy, min_relevance_score: Number(event.target.value) })} /></div>
        <div className="space-y-2"><Label>目標部門（逗號）</Label><Input value={csv(policy.target_departments)} onChange={(event) => setPolicy({ ...policy, target_departments: parseCsv(event.target.value) })} /></div>
        <div className="space-y-2"><Label>目標職稱（逗號）</Label><Input value={csv(policy.target_titles)} onChange={(event) => setPolicy({ ...policy, target_titles: parseCsv(event.target.value) })} /></div>
        <div className="space-y-2"><Label>目標資歷（逗號）</Label><Input value={csv(policy.target_seniorities)} onChange={(event) => setPolicy({ ...policy, target_seniorities: parseCsv(event.target.value) })} /></div>
        <div className="space-y-2"><Label>目標地區（逗號）</Label><Input value={csv(policy.target_locations)} onChange={(event) => setPolicy({ ...policy, target_locations: parseCsv(event.target.value) })} /></div>
        <div className="space-y-2"><Label>排除職稱詞（逗號）</Label><Input value={csv(policy.excluded_title_terms)} onChange={(event) => setPolicy({ ...policy, excluded_title_terms: parseCsv(event.target.value) })} /></div>
        <div className="space-y-2"><Label>每公司候選上限</Label><Input type="number" min={1} max={25} value={policy.max_candidates_per_company} onChange={(event) => setPolicy({ ...policy, max_candidates_per_company: Number(event.target.value) })} /></div>
        <div className="space-y-2"><Label>每日查詢上限</Label><Input type="number" min={0} value={policy.daily_lookup_quota} onChange={(event) => setPolicy({ ...policy, daily_lookup_quota: Number(event.target.value) })} /></div>
        <div className="space-y-2"><Label>每日成本上限</Label><Input type="number" min={0} step={0.01} value={policy.daily_provider_cost_limit} onChange={(event) => setPolicy({ ...policy, daily_provider_cost_limit: Number(event.target.value) })} /></div>
        <div className="space-y-2"><Label>候選保留天數</Label><Input type="number" min={1} max={365} value={policy.candidate_retention_days} onChange={(event) => setPolicy({ ...policy, candidate_retention_days: Number(event.target.value) })} /></div>
        <div className="md:col-span-2 xl:col-span-4"><Button onClick={() => void savePolicy()} disabled={busy === "policy"}><Save className="mr-2 h-4 w-4" />儲存策略</Button></div>
      </CardContent></Card>

      <div className="grid gap-4 md:grid-cols-4"><Card><CardHeader><CardTitle className="text-sm">候選數</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{metrics?.candidate_count ?? 0}</CardContent></Card><Card><CardHeader><CardTitle className="text-sm">平均相關度</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{metrics?.average_relevance.toFixed(1) ?? "—"}</CardContent></Card><Card><CardHeader><CardTitle className="text-sm">Verified 比例</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{metrics?.verified_rate == null ? "樣本不足" : `${(metrics.verified_rate * 100).toFixed(1)}%`}</CardContent></Card><Card><CardHeader><CardTitle className="text-sm">人工核准率</CardTitle></CardHeader><CardContent className="text-2xl font-bold">{metrics?.approval_rate == null ? "樣本不足" : `${(metrics.approval_rate * 100).toFixed(1)}%`}</CardContent></Card></div>

      <Card><CardHeader><CardTitle>已確認公司</CardTitle><p className="text-sm text-muted-foreground">只有 current confirmed company 可排程；工作 payload 不含 IP 或個人資料。</p></CardHeader><CardContent>{companies.length === 0 ? <p className="py-6 text-center text-sm text-muted-foreground">沒有可補全的已確認公司。</p> : <div className="flex flex-wrap gap-3">{companies.map((company) => <div key={company.id} className="flex items-center gap-3 rounded-lg border p-3"><div><p className="font-medium">{company.company_name}</p><p className="text-xs text-muted-foreground">{company.domain}</p></div><Button size="sm" variant="outline" disabled={policy.mode !== "review_only" || busy === company.id} onClick={() => void enqueue(company)}><ContactRound className="mr-1 h-4 w-4" />尋找窗口</Button></div>)}</div>}</CardContent></Card>

      <Card><CardHeader><CardTitle>人工審核佇列</CardTitle><p className="text-sm text-muted-foreground">只顯示遮罩 email、來源、新鮮度、相關度與驗證狀態。轉 Contact 後仍不與 visitor 合併。</p></CardHeader><CardContent>{candidates.length === 0 ? <p className="py-8 text-center text-sm text-muted-foreground">目前沒有聯絡窗口候選。</p> : <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="border-b text-left text-muted-foreground"><th className="p-3">公司／候選</th><th className="p-3">相關度</th><th className="p-3">信箱品質</th><th className="p-3">來源／新鮮度</th><th className="p-3">狀態</th><th className="p-3 text-right">人工動作</th></tr></thead><tbody>{candidates.map((candidate) => <tr key={candidate.id} className="border-b last:border-0"><td className="p-3"><p className="font-medium">{candidate.full_name}</p><p>{candidate.job_title || candidate.department || "未提供職能"}</p><p className="text-xs text-muted-foreground">{candidate.company_name} · {candidate.email_masked}</p></td><td className="p-3"><p className="font-semibold">{candidate.relevance_score}/100</p><p className="max-w-52 text-xs text-muted-foreground">{candidate.relevance_reasons.join("、")}</p></td><td className="p-3"><Badge variant={verificationVariant(candidate.verification_status)}>{candidate.verification_status}</Badge></td><td className="p-3"><p>{candidate.source_provider}</p><p className="text-xs text-muted-foreground">{candidate.source_freshness ? new Date(candidate.source_freshness).toLocaleDateString("zh-TW") : "時間未知"}</p></td><td className="p-3"><Badge variant={candidate.status === "converted" ? "success" : candidate.status === "do_not_contact" || candidate.status === "rejected" ? "destructive" : "outline"}>{candidate.status}</Badge></td><td className="p-3"><div className="flex justify-end gap-2">{candidate.status === "candidate" && <><Button size="sm" variant="outline" disabled={busy === candidate.id} onClick={() => void review(candidate, "reject")}><XCircle className="h-4 w-4" /></Button><Button size="sm" variant="outline" disabled={busy === candidate.id} onClick={() => void review(candidate, "do_not_contact")}><ShieldBan className="h-4 w-4" /></Button><Button size="sm" disabled={busy === candidate.id || candidate.verification_status === "invalid"} onClick={() => void review(candidate, "approve")}><CheckCircle2 className="mr-1 h-4 w-4" />核准</Button></>}{candidate.status === "approved" && <Button size="sm" disabled={busy === candidate.id || candidate.verification_status !== "verified" || candidate.relevance_score < policy.min_relevance_score} onClick={() => void convert(candidate)}><UserPlus className="mr-1 h-4 w-4" />轉 Contact</Button>}</div></td></tr>)}</tbody></table></div>}</CardContent></Card>
    </>}
  </div>;
}
