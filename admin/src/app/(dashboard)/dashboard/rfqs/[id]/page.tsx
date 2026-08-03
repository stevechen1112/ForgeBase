"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth/store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Sparkles, Bot, CheckCircle2, XCircle, Clock } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { agentosApi, type RunView } from "@/lib/api/agentos";

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

  // AgentOS run lookup
  const [agentRunId, setAgentRunId] = useState("");
  const [agentRunView, setAgentRunView] = useState<RunView | null>(null);
  const [agentRunLoading, setAgentRunLoading] = useState(false);
  const [agentRunError, setAgentRunError] = useState("");

  // Timeline events
  const [events, setEvents] = useState<RFQEvent[]>([]);

  async function fetchEvents() {
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/events`, {
        headers: buildApiHeaders(token),
      });
      if (res.ok) setEvents(await res.json());
    } catch { /* non-critical */ }
  }

  async function fetchAssist() {
    try {
      const res = await fetch(`${API_BASE}/tracking/rfqs/${id}/reply-assist`, {
        headers: buildApiHeaders(token),
      });
      if (res.ok) setAssist(await res.json());
    } catch { /* non-critical */ }
  }

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
      setMessage("未成交原因已儲存 ✓");
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
  }, [id, token]);

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
      setMessage("Status updated ✓");
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
      setMessage("Assigned ✓");
      fetchEvents();
    } catch (e) { setMessage(`Error: ${e instanceof Error ? e.message : "unknown"}`); }
    finally { setSaving(false); }
  }

  if (loading) return <div className="py-12 text-center text-muted-foreground">載入中…</div>;
  if (!rfq) return <div className="py-12 text-center text-destructive">RFQ not found</div>;

  const formData = rfq.form_data ?? {};

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center gap-3">
        <Button asChild variant="ghost" size="sm" className="-ml-2">
          <Link href="/dashboard/rfqs">← RFQs</Link>
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">{rfq.rfq_number}</h1>
        <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${PRIORITY_VARIANT[rfq.priority] ?? "bg-muted text-muted-foreground"}`}>
          {rfq.priority}
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
            <CardHeader className="pb-2"><CardTitle className="text-base">Contact Information</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                {[
                  ["Full Name", formData.full_name], ["Email", formData.email],
                  ["Company", formData.company_name], ["Phone", formData.phone],
                  ["Country", formData.country], ["Job Title", formData.job_title],
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
            <CardHeader className="pb-2"><CardTitle className="text-base">Request Details</CardTitle></CardHeader>
            <CardContent>
              <dl className="space-y-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">Quantity</dt>
                  <dd>{String(formData.quantity ?? "—")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Timeline</dt>
                  <dd>{String(formData.timeline ?? "—")}</dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Technical Specifications</dt>
                  <dd className="mt-1 whitespace-pre-wrap rounded bg-muted border p-3 font-mono text-xs">
                    {String(formData.specifications ?? "—")}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Additional Message</dt>
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
            <CardHeader className="pb-2"><CardTitle className="text-base">Tracking</CardTitle></CardHeader>
            <CardContent>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                {[
                  ["Intent Score", rfq.intent_score_at_submit], ["Source Page", rfq.source_page],
                  ["Visitor ID", rfq.visitor_id], ["Contact ID", rfq.contact_id],
                  ["Submitted", new Date(rfq.created_at).toLocaleString()],
                  ["Last Updated", new Date(rfq.updated_at).toLocaleString()],
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
                <CardTitle className="text-base text-indigo-800">AI Analysis</CardTitle>
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
                      <div className="text-xs text-muted-foreground">Match Score</div>
                    </div>
                    <div className={`rounded-lg border px-4 py-2 text-center ${
                      analysis.urgency_level === "high" ? "bg-red-50 border-red-200" :
                      analysis.urgency_level === "medium" ? "bg-amber-50 border-amber-200" : "bg-green-50 border-green-200"
                    }`}>
                      <div className="text-lg font-bold capitalize">{analysis.urgency_level}</div>
                      <div className="text-xs text-muted-foreground">Urgency</div>
                    </div>
                    <div className="rounded-lg bg-white border border-indigo-100 px-4 py-2 text-center">
                      <div className="text-sm font-semibold uppercase">{analysis.language_detected}</div>
                      <div className="text-xs text-muted-foreground">Language</div>
                    </div>
                  </div>
                  <div className="rounded bg-white border border-indigo-100 p-3">
                    <div className="text-xs font-semibold text-muted-foreground mb-1">Summary</div>
                    <p>{analysis.summary}</p>
                  </div>
                  {analysis.key_requirements.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Key Requirements</div>
                      <ul className="list-disc list-inside space-y-0.5">{analysis.key_requirements.map((r, i) => <li key={i}>{r}</li>)}</ul>
                    </div>
                  )}
                  {analysis.matched_products.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Matched Products</div>
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
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Unmet Requirements</div>
                      <ul className="list-disc list-inside text-amber-700 space-y-0.5">{analysis.unmet_requirements.map((r, i) => <li key={i}>{r}</li>)}</ul>
                    </div>
                  )}
                  {analysis.recommended_actions.length > 0 && (
                    <div>
                      <div className="text-xs font-semibold text-muted-foreground mb-1">Recommended Actions</div>
                      <ul className="list-disc list-inside text-blue-700 space-y-0.5">{analysis.recommended_actions.map((a, i) => <li key={i}>{a}</li>)}</ul>
                    </div>
                  )}
                  <div className="border-t border-indigo-200 pt-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs font-semibold text-muted-foreground">Draft Reply Email</div>
                      <Button size="sm" variant="outline" onClick={generateReply} disabled={replyLoading} className="border-indigo-300 text-indigo-700 hover:bg-indigo-50">
                        {replyLoading && <Loader2 className="h-3.5 w-3.5 animate-spin mr-1" />}
                        {replyLoading ? "Generating…" : reply ? "Regenerate" : "Generate Draft"}
                      </Button>
                    </div>
                    {reply && (
                      <div className="rounded bg-white border border-indigo-100 p-3 space-y-2">
                        <div className="text-xs text-muted-foreground">Subject: <span className="font-medium text-foreground">{reply.subject}</span></div>
                        <pre className="whitespace-pre-wrap text-xs font-sans leading-relaxed max-h-64 overflow-y-auto">{reply.body}</pre>
                        <button onClick={() => navigator.clipboard.writeText(`Subject: ${reply.subject}\n\n${reply.body}`)} className="text-xs text-indigo-600 hover:underline">
                          Copy to clipboard
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
            <CardHeader className="pb-2"><CardTitle className="text-sm">Update Status</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <select className={SELECT_CLS} value={newStatus} onChange={(e) => setNewStatus(e.target.value)}>
                {STATUSES.map((s) => <option key={s} value={s}>{s.replace("_", " ")}</option>)}
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
                Update Status
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Assign To</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">User UUID</Label>
                <Input value={assignTo} onChange={(e) => setAssignTo(e.target.value)} placeholder="User UUID" className="font-mono text-xs" />
              </div>
              <Button variant="secondary" className="w-full" onClick={saveAssign} disabled={saving || !assignTo}>
                Assign
              </Button>
              {rfq.assigned_to && (
                <p className="text-xs text-muted-foreground truncate">Current: {rfq.assigned_to}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm">Notifications</CardTitle></CardHeader>
            <CardContent>
              <ul className="space-y-1.5 text-xs">
                {[
                  ["Assigned notified", rfq.assigned_notified_at],
                  ["24h reminder", rfq.reminder_24h_sent_at],
                  ["48h escalation", rfq.escalation_48h_sent_at],
                ].map(([label, dt]) => (
                  <li key={String(label)} className="flex justify-between">
                    <span className="text-muted-foreground">{label}</span>
                    <span className={dt ? "text-green-600" : "text-muted-foreground/50"}>
                      {dt ? new Date(String(dt)).toLocaleDateString() : "pending"}
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
                  <Label className="text-xs">未成交原因</Label>
                  <textarea
                    className="flex w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
                    rows={2}
                    value={lostReason}
                    onChange={(e) => setLostReason(e.target.value)}
                    placeholder="請記錄未成交原因..."
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

          {/* AgentOS run lookup */}
          <Card className="border-indigo-200">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm flex items-center gap-1.5">
                <Bot className="h-4 w-4 text-indigo-500" />
                AgentOS 任務
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1.5">
                <Label className="text-xs">輸入 Run ID 查詢狀態</Label>
                <div className="flex gap-1.5">
                  <Input
                    value={agentRunId}
                    onChange={(e) => setAgentRunId(e.target.value)}
                    placeholder="run_id…"
                    className="font-mono text-xs h-8"
                  />
                  <Button
                    size="sm"
                    variant="outline"
                    className="h-8 shrink-0"
                    disabled={!agentRunId.trim() || agentRunLoading}
                    onClick={async () => {
                      setAgentRunLoading(true); setAgentRunError("");
                      try {
                        const view = await agentosApi.getRun(agentRunId.trim());
                        setAgentRunView(view);
                      } catch (e) {
                        setAgentRunError(e instanceof Error ? e.message : "查詢失敗");
                        setAgentRunView(null);
                      } finally { setAgentRunLoading(false); }
                    }}
                  >
                    {agentRunLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : "查詢"}
                  </Button>
                </div>
              </div>
              {agentRunError && <p className="text-xs text-red-600">{agentRunError}</p>}
              {agentRunView && (() => {
                const run = agentRunView.run;
                const statusCls: Record<string, string> = {
                  waiting_approval: "text-amber-700 bg-amber-50",
                  running: "text-blue-700 bg-blue-50",
                  completed: "text-green-700 bg-green-50",
                  failed: "text-red-700 bg-red-50",
                };
                const pendingApprovals = agentRunView.approvals.filter((a) => a.decision === "pending");
                return (
                  <div className="space-y-2 rounded-lg border bg-indigo-50/40 px-3 py-2.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">狀態</span>
                      <span className={`rounded px-1.5 py-0.5 font-medium ${statusCls[run.status] ?? "bg-muted text-muted-foreground"}`}>
                        {run.status}
                      </span>
                    </div>
                    <div className="text-muted-foreground">{agentRunView.run_state.summary}</div>
                    {pendingApprovals.length > 0 && (
                      <div className="rounded bg-amber-100 px-2 py-1.5 text-amber-800">
                        <Clock className="inline h-3 w-3 mr-1" />
                        {pendingApprovals.length} 項待審批 —{" "}
                        <Link href="/dashboard/agent-runs" className="underline">前往審批</Link>
                      </div>
                    )}
                    {agentRunView.approvals.filter((a) => a.decision !== "pending").map((a) => (
                      <div key={a.id} className="flex items-center gap-1">
                        {a.decision === "approved"
                          ? <CheckCircle2 className="h-3 w-3 text-green-600" />
                          : <XCircle className="h-3 w-3 text-red-600" />}
                        <span className="text-muted-foreground">{a.checkpoint}: {a.decision}</span>
                      </div>
                    ))}
                  </div>
                );
              })()}
              <Link href="/dashboard/agent-runs" className="flex items-center gap-1.5 text-xs text-indigo-600 hover:underline">
                <Bot className="h-3 w-3" />
                查看全部 Agent 任務佇列
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
