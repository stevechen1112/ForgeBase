"use client";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Sparkles, CheckCircle2, XCircle } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { authApi, type TeamMember } from "@/lib/api/auth";

const SELECT_CLS = "flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 text-foreground";

type RFQEvent = {
  id: string;
  event_type: string;
  summary: string;
  detail: Record<string, unknown> | null;
  actor_id: string | null;
  created_at: string;
};

const EVENT_ICON: Record<string, string> = {
  created: "🟢",
  status_changed: "🔄",
  assigned: "👤",
  first_response: "💬",
  quote_sent: "📨",
  lost_reason_set: "❌",
  notification_sent: "🔔",
  ai_analysis_run: "🤖",
  draft_reply_generated: "✉️",
};

type RFQDetail = {
  id: string; rfq_number: string; contact_id: string | null; visitor_id: string | null;
  status: string; priority: string; intent_score_at_submit: number; assigned_to: string | null;
  application_id: string | null; source_page: string | null; hubspot_deal_id: string | null;
  product_ids: string[]; form_data: Record<string, unknown> | null;
  assigned_notified_at: string | null; reminder_24h_sent_at: string | null;
  escalation_48h_sent_at: string | null; closed_at: string | null;
  created_at: string; updated_at: string;
  first_response_at: string | null; quote_sent_at: string | null;
  lost_reason: string | null; won_reason: string | null;
  quality_score: number | null;
  sla_due_at: string | null; sla_breached: boolean;
  quality_reasons?: string[];
  incoterm?: string | null; annual_volume?: string | null;
  is_trial_order?: boolean | null; target_price?: string | null;
  required_certs?: string[]; buyer_timezone?: string | null;
};

type RFQAnalysis = {
  match_score: number; urgency_level: string; key_requirements: string[];
  matched_products: { id: string; name: string; reason: string }[];
  unmet_requirements: string[]; recommended_actions: string[];
  summary: string; language_detected: string;
};
type DraftReply = { subject: string; body: string; language: string };

// §5.4 回覆品質輔助
type ReplyAssist = {
  checklist: { key: string; label: string; ok: boolean; ask: string | null }[];
  quote_readiness: { score: number; ready: boolean; gaps: string[]; message: string };
  suggested_questions: string[];
  templates: { id: string; name: string; body: string }[];
  buyer_country: string | null;
};

const STATUSES = ["new", "assigned", "in_progress", "quoted", "negotiation", "won", "lost", "expired"];
const STATUS_LABEL: Record<string, string> = {
  new: "新進",
  assigned: "已指派",
  in_progress: "處理中",
  quoted: "已報價",
  negotiation: "談判中",
  won: "成交",
  lost: "流失",
  expired: "過期",
};
const PRIORITY_LABEL: Record<string, string> = {
  normal: "一般",
  high: "高",
  urgent: "緊急",
};
const PRIORITY_VARIANT: Record<string, string> = {
  urgent: "bg-red-100 text-red-700",
  high: "bg-orange-100 text-orange-700",
  normal: "bg-muted text-muted-foreground",
};

export default function RFQDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  const [rfq, setRfq] = useState<RFQDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [newStatus, setNewStatus] = useState("");
  const [assignTo, setAssignTo] = useState("");
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  const [analysis, setAnalysis] = useState<RFQAnalysis | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState("");
  const [reply, setReply] = useState<DraftReply | null>(null);
  const [replyLoading, setReplyLoading] = useState(false);
  const [closeReason, setCloseReason] = useState("");
  const [assist, setAssist] = useState<ReplyAssist | null>(null);

  // Follow-up state
  const [followUpSaving, setFollowUpSaving] = useState(false);
  const [lostReason, setLostReason] = useState("");

  // Timeline events
  const [events, setEvents] = useState<RFQEvent[]>([]);

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/events`, {
        headers: buildApiHeaders(token),
      });
      if (res.ok) setEvents(await res.json());
    } catch { /* non-critical */ }
  }, [id, token]);

  const fetchAssist = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/reply-assist`, {
        headers: buildApiHeaders(token),
      });
      if (res.ok) setAssist(await res.json());
    } catch { /* non-critical */ }
  }, [id, token]);

  async function saveFollowUp(field: "first_response_at" | "quote_sent_at") {
    setFollowUpSaving(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/follow-up`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ [field]: new Date().toISOString() }),
      });
      if (!res.ok) throw new Error("Failed");
      setRfq((prev) => prev ? { ...prev, [field]: new Date().toISOString() } : prev);
      setMessage(`${field === "first_response_at" ? "首次回覆" : "報價發出"}時間已記錄 ✓`);
      fetchEvents();
    } catch (e) { setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`); }
    finally { setFollowUpSaving(false); }
  }

  async function saveLostReason() {
    if (!lostReason.trim()) return;
    setFollowUpSaving(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/follow-up`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ lost_reason: lostReason }),
      });
      if (!res.ok) throw new Error("Failed");
      setRfq((prev) => prev ? { ...prev, lost_reason: lostReason } : prev);
      setMessage("流失原因已儲存 ✓");
      fetchEvents();
    } catch (e) { setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`); }
    finally { setFollowUpSaving(false); }
  }

  async function runAnalysis() {
    setAnalysisLoading(true); setAnalysisError("");
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/analyze`, {
        method: "POST", headers: buildApiHeaders(token),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Analysis failed");
      setAnalysis(data);
    } catch (e) { setAnalysisError(e instanceof Error ? e.message : "Unknown error"); }
    finally { setAnalysisLoading(false); }
  }

  async function generateReply() {
    setReplyLoading(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/draft-reply`, {
        method: "POST",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ analysis }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Draft generation failed");
      setReply(data);
    } catch (e) { setAnalysisError(e instanceof Error ? e.message : "Unknown error"); }
    finally { setReplyLoading(false); }
  }

  useEffect(() => {
    fetch(`${API_BASE}/tracking/rfqs/${id}`, { headers: buildApiHeaders(token) })
      .then((r) => r.json())
      .then((data) => { setRfq(data); setNewStatus(data.status); setAssignTo(data.assigned_to ?? ""); })
      .finally(() => setLoading(false));
    fetchEvents();
    fetchAssist();
    if (token) {
      authApi.listTeam(token)
        .then((members) => setTeamMembers(members.filter((member) => member.is_active)))
        .catch(() => setTeamMembers([]));
    }
  }, [fetchAssist, fetchEvents, id, token]);

  async function saveStatus() {
    if (!rfq || newStatus === rfq.status) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/status`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({
          status: newStatus,
          ...(closeReason.trim() ? { reason: closeReason.trim() } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        const d = data.detail;
        const msg = typeof d === "string"
          ? d
          : Array.isArray(d)
            ? d.map((x: { msg?: string }) => x?.msg || JSON.stringify(x)).join("; ")
            : (d ? JSON.stringify(d) : res.statusText);
        throw new Error(msg);
      }
      setRfq((prev) => prev ? { ...prev, status: data.status, ...(newStatus === "won" && closeReason.trim() ? { won_reason: closeReason.trim() } : {}), ...(newStatus === "lost" && closeReason.trim() ? { lost_reason: closeReason.trim() } : {}) } : prev);
      setCloseReason("");
      setMessage("狀態已更新 ✓");
      fetchEvents();
    } catch (e) { setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`); }
    finally { setSaving(false); }
  }

  async function saveAssign() {
    if (!rfq || !assignTo) return;
    setSaving(true);
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/assign`, {
        method: "PUT",
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
        body: JSON.stringify({ assigned_to: assignTo }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      setRfq((prev) => prev ? { ...prev, assigned_to: data.assigned_to, status: data.status } : prev);
      setMessage("已指派 ✓");
      fetchEvents();
    } catch (e) { setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="py-12 text-center text-muted-foreground">載入中…</div>;
  if (!rfq) return <div className="py-12 text-center text-destructive">找不到 RFQ</div>;

  const formData = rfq.form_data ?? {};
  const assignedMember = teamMembers.find((member) => member.id === rfq.assigned_to);

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/dashboard/rfqs">← 返回列表</Link>
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">{rfq.rfq_number}</h1>
        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${PRIORITY_VARIANT[rfq.priority] ?? "bg-muted text-muted-foreground"}`}>
          {PRIORITY_LABEL[rfq.priority] ?? rfq.priority}
        </span>
      </div>

      {message && (
        <Alert className="mb-4">
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main info */}
        <div className="lg:col-span-2 space-y-5">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">聯絡資訊</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                {[
                  ["姓名", formData.full_name], ["Email", formData.email],
                  ["公司", formData.company_name], ["電話", formData.phone],
                  ["國家", formData.country], ["職稱", formData.job_title],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <dt className="text-xs text-muted-foreground">{String(label)}</dt>
                    <dd className="font-medium">{String(value ?? "—")}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">需求內容</CardTitle></CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">數量</dt>
                  <dd>{String(formData.quantity ?? "—")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">期望交期</dt>
                  <dd>{String(formData.timeline ?? "—")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">技術規格</dt>
                  <dd className="mt-1 whitespace-pre-wrap rounded bg-muted border p-3 font-mono text-xs">
                    {String(formData.specifications ?? "—")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">補充訊息</dt>
                  <dd className="whitespace-pre-wrap">{String(formData.message ?? "—")}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">品質分數與貿易條件</CardTitle></CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex items-center gap-3">
                <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold ${
                  (rfq.quality_score ?? 0) >= 70 ? "bg-green-100 text-green-800"
                  : (rfq.quality_score ?? 0) >= 40 ? "bg-yellow-100 text-yellow-800"
                  : "bg-gray-100 text-gray-600"
                }`}>
                  品質 {rfq.quality_score ?? "—"}/100
                </span>
                {rfq.sla_breached ? (
                  <span className="inline-flex items-center rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">SLA 已逾期</span>
                ) : rfq.sla_due_at ? (
                  <span className="text-xs text-muted-foreground">SLA 截止 {new Date(rfq.sla_due_at).toLocaleString("zh-TW")}</span>
                ) : null}
              </div>
              {(rfq.quality_reasons?.length ?? 0) > 0 && (
                <ul className="list-disc list-inside space-y-0.5 text-muted-foreground">
                  {rfq.quality_reasons!.map((r, i) => <li key={i}>{r}</li>)}
                </ul>
              )}
              <dl className="grid grid-cols-2 gap-3">
                <div>
                  <dt className="text-xs text-muted-foreground">Incoterm</dt>
                  <dd className="font-medium">{rfq.incoterm ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">預估年採購量</dt>
                  <dd className="font-medium">{rfq.annual_volume ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">目標價格</dt>
                  <dd className="font-medium">{rfq.target_price ?? "—"}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">試單</dt>
                  <dd className="font-medium">{rfq.is_trial_order == null ? "—" : rfq.is_trial_order ? "是" : "否"}</dd>
                </div>
                {(rfq.required_certs?.length ?? 0) > 0 && (
                  <div className="col-span-2">
                    <dt className="text-xs text-muted-foreground">需求認證</dt>
                    <dd className="font-medium">{rfq.required_certs!.join("、")}</dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-base">追蹤資訊</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ["意圖分數", rfq.intent_score_at_submit], ["來源頁", rfq.source_page],
                  ["訪客 ID", rfq.visitor_id], ["聯絡人 ID", rfq.contact_id],
                  ["提交時間", new Date(rfq.created_at).toLocaleString()],
                  ["最後更新", new Date(rfq.updated_at).toLocaleString()],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <dt className="text-xs text-muted-foreground">{String(label)}</dt>
                    <dd className="font-medium truncate max-w-[200px]">{String(value ?? "—")}</dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>

          {/* Activity Timeline */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">活動紀錄</CardTitle>
                <Button size="sm" variant="ghost" onClick={fetchEvents} className="text-xs">
                  重新整理
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground">尚無紀錄</p>
              ) : (
                <ol className="relative border-l border-muted-foreground/20 ml-2 space-y-4">
                  {events.map((evt) => (
                    <li key={evt.id} className="ml-4">
                      <div className="absolute -left-2.5 mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-background border text-xs">
                        {EVENT_ICON[evt.event_type] ?? "📌"}
                      </div>
                      <div className="flex items-baseline justify-between gap-2">
                        <p className="text-sm font-medium">{evt.summary}</p>
                        <time className="shrink-0 text-xs text-muted-foreground">
                          {new Date(evt.created_at).toLocaleString()}
                        </time>
                      </div>
                      {evt.detail && (
                        <pre className="mt-1 text-xs text-muted-foreground bg-muted rounded px-2 py-1 overflow-x-auto">
                          {JSON.stringify(evt.detail, null, 2)}
                        </pre>
                      )}
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>

          {/* 回覆品質輔助 Panel（§5.4） */}
          {assist && (
            <Card className="border-emerald-200 bg-emerald-50/30">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base text-emerald-800">回覆前檢查（Quote Readiness）</CardTitle>
                  <span className={`rounded-full px-2.5 py-1 text-xs font-bold ${assist.quote_readiness.ready ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>
                    {assist.quote_readiness.score} 分 — {assist.quote_readiness.message}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                <ul className="space-y-1.5">
                  {assist.checklist.map((item) => (
                    <li key={item.key} className="flex items-start gap-2">
                      {item.ok
                        ? <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                        : <XCircle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />}
                      <span className={item.ok ? "text-muted-foreground" : "font-medium"}>{item.label}</span>
                    </li>
                  ))}
                </ul>
                {assist.suggested_questions.length > 0 && (
                  <div className="border-t border-emerald-200 pt-3">
                    <p className="mb-1.5 text-xs font-semibold text-muted-foreground">建議反問買家</p>
                    <ul className="list-inside list-disc space-y-1 text-xs">
                      {assist.suggested_questions.map((q, i) => <li key={i}>{q}</li>)}
                    </ul>
                  </div>
                )}
                {assist.templates.length > 0 && (
                  <div className="border-t border-emerald-200 pt-3">
                    <p className="mb-1.5 text-xs font-semibold text-muted-foreground">
                      匹配範本{assist.buyer_country ? `（買家國家：${assist.buyer_country}）` : ""}
                    </p>
                    {assist.templates.map((t) => (
                      <details key={t.id} className="mb-1.5 rounded border bg-background px-3 py-2 text-xs">
                        <summary className="cursor-pointer font-medium">{t.name}</summary>
                        <pre className="mt-2 whitespace-pre-wrap font-sans text-muted-foreground">{t.body}</pre>
                      </details>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          )}

          {/* AI Analysis Panel */}
          <Card className="border-indigo-200 bg-indigo-50/30">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base text-indigo-800">AI 分析</CardTitle>
                <Button
                  size="sm"
                  onClick={runAnalysis}
                  disabled={analysisLoading}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white"
                >
                  {analysisLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Sparkles className="h-3.5 w-3.5" />}
                  <span className="ml-1.5">{analysisLoading ? "分析中…" : analysis ? "重新分析" : "執行 AI 分析"}</span>
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {analysisError && (
                <Alert variant="destructive" className="mb-3">
                  <AlertDescription>{analysisError}</AlertDescription>
                </Alert>
              )}
              {analysis && (
                <div className="space-y-4 text-sm">
                  <div className="flex gap-4">
                    <div className="rounded-lg bg-white border border-indigo-100 px-4 py-2 text-center">
                      <div className="text-2xl font-bold text-indigo-700">{analysis.match_score}</div>
                      <div className="text-xs text-muted-foreground">媒合分數</div>
                    </div>
                    <div className={`rounded-lg border px-4 py-2 text-center ${
                      analysis.urgency_level === "high" ? "bg-red-50 border-red-200" :
                      analysis.urgency_level === "medium" ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-200"
                    }`}>
                      <div className="text-lg font-bold">{({ high: "高", medium: "中", low: "低" } as Record<string, string>)[analysis.urgency_level] ?? analysis.urgency_level}</div>
                      <div className="text-xs text-muted-foreground">急迫性</div>
                    </div>
                    <div className="rounded-lg bg-white border border-indigo-100 px-4 py-2 text-center">
                      <div className="text-sm font-semibold uppercase">{analysis.language_detected}</div>
                      <div className="text-xs text-muted-foreground">語言</div>
                    </div>
                  </div>
                  <div className="rounded bg-white border border-indigo-100 p-3">
                    <div className="text-xs font-semibold text-muted-foreground mb-1">摘要</div>
                    <p>{analysis.summary}</p>
                  </div>
                  {analysis.key_requirements.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">關鍵需求</div>
                      <ul className="list-disc list-inside space-y-0.5">{analysis.key_requirements.map((r, i) => <li key={i}>{r}</li>)}</ul>
                    </div>
                  )}
                  {analysis.matched_products.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">匹配商品</div>
                      <div className="space-y-1">
                        {analysis.matched_products.map((p, i) => (
                          <div key={i} className="rounded bg-green-50 border border-green-100 px-3 py-1.5">
                            <span className="font-medium text-green-800">{p.name}</span>
                            {p.reason && <span className="ml-2 text-xs text-muted-foreground">— {p.reason}</span>}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {analysis.unmet_requirements.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">未滿足需求</div>
                      <ul className="list-disc list-inside text-amber-700 space-y-0.5">{analysis.unmet_requirements.map((r, i) => <li key={i}>{r}</li>)}</ul>
                    </div>
                  )}
                  {analysis.recommended_actions.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">建議行動</div>
                      <ul className="list-disc list-inside text-blue-700 space-y-0.5">{analysis.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
                    </div>
                  )}
                  <div className="border-t border-indigo-200 pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs font-semibold text-muted-foreground">AI 草稿回覆信</div>
                      <Button size="sm" variant="outline" onClick={generateReply} disabled={replyLoading} className="border-indigo-300 text-indigo-700 hover:bg-indigo-50">
                        {replyLoading && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
                        {replyLoading ? "產生中…" : reply ? "重新產生" : "產生草稿"}
                      </Button>
                    </div>
                    {reply && (
                      <div className="rounded bg-white border border-indigo-100 p-3 space-y-2">
                        <div className="text-xs text-muted-foreground">主旨：<span className="font-medium text-foreground">{reply.subject}</span></div>
                        <pre className="whitespace-pre-wrap text-xs font-sans leading-relaxed max-h-64 overflow-y-auto">{reply.body}</pre>
                        <button onClick={() => navigator.clipboard.writeText(`Subject: ${reply.subject}\n\n${reply.body}`)} className="text-xs text-indigo-600 hover:underline">
                          複製到剪貼簿
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Actions sidebar */}
        <div className="space-y-4">
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">更新狀態</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <select className={SELECT_CLS} value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{STATUS_LABEL[s] ?? s}</option>)}
              </select>
              {(newStatus === "won" || newStatus === "lost") && (
                <div className="space-y-1.5">
                  <Label className="text-xs">
                    {newStatus === "won" ? "成交原因（必填）" : "流失原因（必填）"}
                  </Label>
                  <Input
                    value={closeReason}
                    onChange={(e) => setCloseReason(e.target.value)}
                    placeholder={newStatus === "won" ? "例：價格與交期具競爭力" : "例：報價高於競爭對手 15%"}
                    className="text-xs"
                  />
                </div>
              )}
              <Button
                className="w-full"
                onClick={saveStatus}
                disabled={saving || newStatus === rfq.status || ((newStatus === "won" || newStatus === "lost") && !closeReason.trim() && !((newStatus === "won" && rfq.won_reason) || (newStatus === "lost" && rfq.lost_reason)))}
              >
                {saving && <Loader2 className="h-4 w-4 animate-spin mr-1" />}
                更新狀態
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">指派負責人</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">成員編號</Label>
                <select
                  id="rfq-assignee"
                  value={assignTo}
                  onChange={(e) => setAssignTo(e.target.value)}
                  className={SELECT_CLS}
                  aria-label="選擇負責成員"
                >
                  <option value="">請選擇負責成員</option>
                  {rfq.assigned_to && !assignedMember && (
                    <option value={rfq.assigned_to}>目前負責人（帳號已停用或不存在）</option>
                  )}
                  {teamMembers.map((member) => (
                    <option key={member.id} value={member.id}>
                      {member.full_name || member.email}（{member.role}）
                    </option>
                  ))}
                </select>
              </div>
              <Button variant="secondary" className="w-full" onClick={saveAssign} disabled={saving || !assignTo}>
                指派
              </Button>
              {rfq.assigned_to && (
                <p className="text-xs text-muted-foreground truncate">
                  目前：{assignedMember?.full_name || assignedMember?.email || "帳號已停用或不存在"}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">通知紀錄</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-1.5 text-xs">
                {[
                  ["指派通知", rfq.assigned_notified_at],
                  ["24h 提醒", rfq.reminder_24h_sent_at],
                  ["48h 升級", rfq.escalation_48h_sent_at],
                ].map(([label, dt]) => (
                  <li key={String(label)} className="flex justify-between">
                    <span className="text-muted-foreground">{label}</span>
                    <span className={dt ? "text-green-600" : "text-muted-foreground/50"}>
                      {dt ? new Date(String(dt)).toLocaleDateString() : "待發送"}
                    </span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          {/* Sales Follow-up Tracking */}
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">銷售跟進</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">首次回覆</span>
                {rfq.first_response_at ? (
                  <span className="text-xs text-green-600">{new Date(rfq.first_response_at).toLocaleDateString()}</span>
                ) : (
                  <Button size="sm" variant="outline" disabled={followUpSaving} onClick={() => saveFollowUp("first_response_at")}>記錄</Button>
                )}
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs text-muted-foreground">報價發出</span>
                {rfq.quote_sent_at ? (
                  <span className="text-xs text-green-600">{new Date(rfq.quote_sent_at).toLocaleDateString()}</span>
                ) : (
                  <Button size="sm" variant="outline" disabled={followUpSaving} onClick={() => saveFollowUp("quote_sent_at")}>記錄</Button>
                )}
              </div>
              {rfq.status === "lost" && (
                <div className="space-y-1.5">
                  <Label className="text-xs">流失原因</Label>
                  <textarea
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                    rows={2}
                    value={lostReason}
                    onChange={(e) => setLostReason(e.target.value)}
                    placeholder="請記錄流失原因..."
                  />
                  <Button size="sm" variant="secondary" className="w-full" disabled={followUpSaving || !lostReason.trim()} onClick={saveLostReason}>
                    儲存原因
                  </Button>
                  {rfq.lost_reason && (
                    <p className="text-xs text-muted-foreground">已記錄: {rfq.lost_reason}</p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

        </div>
      </div>
    </div>
  );
}
