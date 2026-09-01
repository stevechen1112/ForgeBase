"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  AlertTriangle,
  CalendarClock,
  ChevronDown,
  MessageSquareText,
  RefreshCw,
  UserRound,
} from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { authApi, type TeamMember } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

type Contact = {
  id: string;
  full_name: string;
  company_name: string | null;
  email: string;
  phone: string | null;
  country: string | null;
  job_title: string | null;
};

type VisitorEvent = {
  event_name: string;
  timestamp: string;
  page_url: string | null;
  page_type: string | null;
  traffic_source: string | null;
  campaign_id: string | null;
  locale: string | null;
};

type RFQDetail = {
  id: string;
  rfq_number: string;
  status: string;
  priority: string;
  assigned_to: string | null;
  assigned_to_name: string | null;
  next_follow_up_at: string | null;
  contact: Contact | null;
  form_data: Record<string, unknown> | null;
  products: { id: string; name: string; model_number: string }[];
  source_page: string | null;
  visitor_id: string | null;
  visitor_history: VisitorEvent[];
  duplicate_candidates: {
    id: string;
    rfq_number: string;
    status: string;
    created_at: string;
  }[];
  quality_score: number | null;
  quality_reasons?: string[];
  sla_due_at: string | null;
  sla_breached: boolean;
  incoterm?: string | null;
  annual_volume?: string | null;
  is_trial_order?: boolean | null;
  target_price?: string | null;
  required_certs?: string[];
  created_at: string;
  updated_at: string;
  first_response_at: string | null;
  quote_sent_at: string | null;
  won_reason: string | null;
  lost_reason: string | null;
  deal_amount: string | null;
  deal_currency: string;
  is_spam: boolean;
  spam_reason: string | null;
  merged_into_rfq_id: string | null;
};

type RFQEvent = {
  id: string;
  event_type: string;
  summary: string;
  detail: Record<string, unknown> | null;
  actor_id: string | null;
  actor_name?: string | null;
  created_at: string;
};

type RFQNote = {
  id: string;
  body: string;
  author_id: string;
  author_name: string;
  created_at: string;
};

type AttributionDetail = {
  attribution_type: "direct" | "assisted" | "unknown" | "manual";
  confidence: number;
  manually_overridden: boolean;
  override_reason: string | null;
  lineage: Record<string, string | null>;
  evidence: Record<string, unknown>;
  events: {
    id: string;
    action: string;
    previous_type: string | null;
    attribution_type: string;
    reason: string | null;
    created_at: string;
  }[];
};

const STATUS_LABEL: Record<string, string> = {
  new: "待處理",
  assigned: "待處理（已分派）",
  in_progress: "聯繫中",
  quoted: "報價／樣品",
  negotiation: "洽談中",
  won: "已成交",
  lost: "未成交",
  expired: "已結案",
};

const STATUS_STYLE: Record<string, string> = {
  new: "bg-blue-100 text-blue-800",
  assigned: "bg-sky-100 text-sky-800",
  in_progress: "bg-amber-100 text-amber-800",
  quoted: "bg-violet-100 text-violet-800",
  negotiation: "bg-indigo-100 text-indigo-800",
  won: "bg-emerald-100 text-emerald-800",
  lost: "bg-muted text-muted-foreground",
  expired: "bg-slate-100 text-slate-700",
};

const EVENT_LABEL: Record<string, string> = {
  created: "收到詢價",
  status_changed: "更新案件階段",
  assigned: "指派負責業務",
  first_response: "記錄首次回覆",
  quote_sent: "記錄報價發出",
  next_follow_up_set: "設定下次跟進",
  note_added: "新增內部備註",
  spam_marked: "移至垃圾隔離區",
  spam_restored: "從垃圾隔離區還原",
  duplicate_merged: "合併重複詢價",
  merged_into: "案件已被合併",
  notification_sent: "寄送內部提醒",
};

const SELECT_CLS =
  "flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50";

function toLocalInput(value: string | null) {
  if (!value) return "";
  const date = new Date(value);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 16);
}

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

function errorMessage(data: unknown, fallback: string) {
  if (data && typeof data === "object" && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export default function RFQDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const isManager = user?.role === "owner" || user?.role === "admin";
  const canOperate = isManager || user?.role === "sales";

  const [rfq, setRfq] = useState<RFQDetail | null>(null);
  const [events, setEvents] = useState<RFQEvent[]>([]);
  const [notes, setNotes] = useState<RFQNote[]>([]);
  const [attribution, setAttribution] = useState<AttributionDetail | null>(
    null,
  );
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [nextFollowUp, setNextFollowUp] = useState("");
  const [closeReason, setCloseReason] = useState("");
  const [dealAmount, setDealAmount] = useState("");
  const [dealCurrency, setDealCurrency] = useState("USD");
  const [noteBody, setNoteBody] = useState("");
  const [spamReason, setSpamReason] = useState("");

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError("");
    try {
      const [
        detailResponse,
        eventsResponse,
        notesResponse,
        attributionResponse,
      ] = await Promise.all([
        fetch(`${API_BASE}/tracking/rfqs/${id}`, {
          headers: buildApiHeaders(token),
        }),
        fetch(`${API_BASE}/tracking/rfqs/${id}/events`, {
          headers: buildApiHeaders(token),
        }),
        fetch(`${API_BASE}/tracking/rfqs/${id}/notes`, {
          headers: buildApiHeaders(token),
        }),
        fetch(`${API_BASE}/tracking/rfqs/${id}/attribution`, {
          headers: buildApiHeaders(token),
        }),
      ]);
      const detail = await detailResponse.json().catch(() => null);
      if (!detailResponse.ok)
        throw new Error(errorMessage(detail, "找不到詢價案件"));
      setRfq(detail);
      setStatus(detail.status);
      setOwnerId(detail.assigned_to ?? "");
      setNextFollowUp(toLocalInput(detail.next_follow_up_at));
      setDealAmount(detail.deal_amount ?? "");
      setDealCurrency(detail.deal_currency ?? "USD");
      setEvents(eventsResponse.ok ? await eventsResponse.json() : []);
      setNotes(notesResponse.ok ? await notesResponse.json() : []);
      setAttribution(
        attributionResponse.ok ? await attributionResponse.json() : null,
      );
    } catch (cause) {
      setRfq(null);
      setError(cause instanceof Error ? cause.message : "詢價案件載入失敗");
    } finally {
      setLoading(false);
    }
  }, [id, token]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!token || !isManager) return;
    authApi
      .listTeam(token)
      .then((members) =>
        setTeam(
          members.filter(
            (member) =>
              member.is_active &&
              ["sales", "admin", "owner"].includes(member.role),
          ),
        ),
      )
      .catch(() => setTeam([]));
  }, [isManager, token]);

  const form = rfq?.form_data ?? {};
  const isClosedChoice = status === "won" || status === "lost";
  const followUpOverdue = useMemo(
    () =>
      Boolean(
        rfq?.next_follow_up_at &&
        new Date(rfq.next_follow_up_at) < new Date() &&
        !["won", "lost", "expired"].includes(rfq.status),
      ),
    [rfq],
  );

  async function request(path: string, method: string, body: object) {
    const response = await fetch(`${API_BASE}${path}`, {
      method,
      headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    const data = await response.json().catch(() => null);
    if (!response.ok)
      throw new Error(errorMessage(data, `HTTP ${response.status}`));
    return data;
  }

  async function saveStatus() {
    if (!rfq || (status === rfq.status && !isClosedChoice)) return;
    if (
      isClosedChoice &&
      !closeReason.trim() &&
      !(status === "won" ? rfq.won_reason : rfq.lost_reason)
    ) {
      setError(status === "won" ? "請填寫成交原因" : "請填寫未成交原因");
      return;
    }
    if (status === "won" && !dealAmount && !rfq.deal_amount) {
      setError("請填寫成交金額");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await request(`/tracking/rfqs/${id}/status`, "PUT", {
        status,
        ...(closeReason.trim() ? { reason: closeReason.trim() } : {}),
        ...(status === "won" && dealAmount
          ? { deal_amount: dealAmount, deal_currency: dealCurrency }
          : {}),
      });
      setMessage("案件階段已更新");
      setCloseReason("");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "更新失敗");
    } finally {
      setSaving(false);
    }
  }

  async function saveOwner() {
    if (!ownerId) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await request(`/tracking/rfqs/${id}/assign`, "PUT", {
        assigned_to: ownerId,
      });
      setMessage("負責業務已更新");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "指派失敗");
    } finally {
      setSaving(false);
    }
  }

  async function saveFollowUp() {
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await request(`/tracking/rfqs/${id}/follow-up`, "PUT", {
        next_follow_up_at: nextFollowUp
          ? new Date(nextFollowUp).toISOString()
          : null,
      });
      setMessage(nextFollowUp ? "下次跟進時間已設定" : "已清除跟進時間");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "跟進時間更新失敗");
    } finally {
      setSaving(false);
    }
  }

  async function addNote() {
    if (!noteBody.trim()) return;
    setSaving(true);
    setError("");
    setMessage("");
    try {
      await request(`/tracking/rfqs/${id}/notes`, "POST", {
        body: noteBody.trim(),
      });
      setNoteBody("");
      setMessage("內部備註已加入");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "備註儲存失敗");
    } finally {
      setSaving(false);
    }
  }

  async function toggleSpam() {
    if (!rfq) return;
    if (!rfq.is_spam && !spamReason.trim()) {
      setError("請先填寫判定為垃圾詢價的原因");
      return;
    }
    const action = rfq.is_spam ? "還原此詢價" : "移至垃圾隔離區";
    if (!window.confirm(`確定要${action}？案件不會被刪除。`)) return;
    setSaving(true);
    setError("");
    try {
      await request(`/tracking/rfqs/${id}/spam`, "PUT", {
        is_spam: !rfq.is_spam,
        reason: spamReason.trim() || null,
      });
      setMessage(rfq.is_spam ? "詢價已還原" : "詢價已移至垃圾隔離區");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失敗");
    } finally {
      setSaving(false);
    }
  }

  async function mergeDuplicate(
    duplicate: RFQDetail["duplicate_candidates"][number],
  ) {
    if (
      !window.confirm(
        `確定將 ${duplicate.rfq_number} 合併至目前案件？原資料會保留在「已合併案件」。`,
      )
    )
      return;
    setSaving(true);
    setError("");
    try {
      await request(`/tracking/rfqs/${id}/merge`, "POST", {
        duplicate_rfq_id: duplicate.id,
      });
      setMessage(`${duplicate.rfq_number} 已合併`);
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "合併失敗");
    } finally {
      setSaving(false);
    }
  }

  if (loading)
    return (
      <div className="py-14 text-center text-sm text-muted-foreground">
        載入詢價案件…
      </div>
    );
  if (!rfq)
    return (
      <div>
        <Alert variant="destructive">
          <AlertDescription>{error || "找不到詢價案件"}</AlertDescription>
        </Alert>
        <Button
          variant="ghost"
          className="mt-4"
          onClick={() => router.push("/dashboard/rfqs")}
        >
          ← 返回詢價案件
        </Button>
      </div>
    );

  return (
    <div className="max-w-6xl">
      <Button asChild variant="ghost" size="sm" className="mb-3 -ml-2">
        <Link href="/dashboard/rfqs">← 返回詢價案件</Link>
      </Button>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight">
              {rfq.contact?.company_name || "未填公司"}
            </h1>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLE[rfq.status] ?? "bg-muted"}`}
            >
              {STATUS_LABEL[rfq.status] ?? rfq.status}
            </span>
            {rfq.is_spam && (
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                垃圾隔離
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-muted-foreground">
            {rfq.rfq_number} · {rfq.contact?.full_name || "未填聯絡人"} ·{" "}
            {new Date(rfq.created_at).toLocaleString("zh-TW")}
          </p>
        </div>
        {followUpOverdue && (
          <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm font-medium text-red-700">
            <AlertTriangle className="h-4 w-4" />
            跟進已逾期
          </div>
        )}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {message && (
        <Alert className="mb-4 border-emerald-200 bg-emerald-50">
          <AlertDescription className="text-emerald-800">
            {message}
          </AlertDescription>
        </Alert>
      )}
      {!canOperate && (
        <Alert className="mb-4">
          <AlertDescription>
            您目前可以查看案件與來源資訊；案件處理操作由負責業務或主管執行。
          </AlertDescription>
        </Alert>
      )}

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_340px]">
        <div className="space-y-5">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">客戶與詢價需求</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <dl className="grid gap-4 text-sm sm:grid-cols-2 lg:grid-cols-3">
                {[
                  ["聯絡人", rfq.contact?.full_name],
                  ["Email", rfq.contact?.email],
                  ["電話", rfq.contact?.phone],
                  ["國家", rfq.contact?.country],
                  ["職稱", rfq.contact?.job_title],
                  ["期望交期", form.timeline],
                ].map(([label, value]) => (
                  <div key={String(label)}>
                    <dt className="text-xs text-muted-foreground">
                      {String(label)}
                    </dt>
                    <dd className="mt-1 font-medium break-words">
                      {displayValue(value)}
                    </dd>
                  </div>
                ))}
              </dl>
              {rfq.products.length > 0 && (
                <div>
                  <p className="mb-2 text-xs text-muted-foreground">詢問產品</p>
                  <div className="flex flex-wrap gap-2">
                    {rfq.products.map((product) => (
                      <span
                        key={product.id}
                        className="rounded-md border bg-muted/40 px-2.5 py-1.5 text-sm"
                      >
                        {product.name}{" "}
                        <span className="text-xs text-muted-foreground">
                          {product.model_number}
                        </span>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <dl className="grid gap-4 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-xs text-muted-foreground">需求數量</dt>
                  <dd className="mt-1 font-medium">
                    {displayValue(form.quantity)}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">補充訊息</dt>
                  <dd className="mt-1 whitespace-pre-wrap">
                    {displayValue(form.message)}
                  </dd>
                </div>
              </dl>
              <div>
                <p className="text-xs text-muted-foreground">規格與要求</p>
                <div className="mt-1 whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
                  {displayValue(form.specifications)}
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">北極星來源與歸因證據</CardTitle>
            </CardHeader>
            <CardContent>
              {!attribution ? (
                <p className="text-sm text-muted-foreground">
                  此租戶尚未開放閉環歸因，或尚未建立可追溯紀錄。
                </p>
              ) : (
                <div className="space-y-4 text-sm">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full bg-primary/10 px-3 py-1 font-semibold text-primary">
                      {attribution.attribution_type}
                    </span>
                    <span>
                      信心 {Math.round(attribution.confidence * 100)}%
                    </span>
                    {attribution.manually_overridden && (
                      <span className="text-amber-700">人工覆寫</span>
                    )}
                  </div>
                  <p className="text-muted-foreground">
                    {String(
                      attribution.evidence.causal_claim ??
                        attribution.evidence.rule ??
                        "沒有足夠因果證據",
                    )}
                  </p>
                  <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                    {Object.entries(attribution.lineage).map(([key, value]) => (
                      <div key={key}>
                        <dt className="text-xs text-muted-foreground">{key}</dt>
                        <dd className="break-all font-mono text-xs">
                          {value ?? "—"}
                        </dd>
                      </div>
                    ))}
                  </dl>
                  {attribution.override_reason && (
                    <Alert>
                      <AlertDescription>
                        覆寫原因：{attribution.override_reason}
                      </AlertDescription>
                    </Alert>
                  )}
                  <details>
                    <summary className="cursor-pointer font-medium">
                      歸因決策歷程（{attribution.events.length}）
                    </summary>
                    <ol className="mt-3 space-y-2 border-l pl-4">
                      {attribution.events.map((event) => (
                        <li key={event.id}>
                          <p>
                            {event.action} · {event.attribution_type}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            {event.reason ?? "—"} ·{" "}
                            {new Date(event.created_at).toLocaleString("zh-TW")}
                          </p>
                        </li>
                      ))}
                    </ol>
                  </details>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquareText className="h-4 w-4" />
                內部備註
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {canOperate && (
                <div className="space-y-2">
                  <textarea
                    className="min-h-24 w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    value={noteBody}
                    onChange={(event) => setNoteBody(event.target.value)}
                    placeholder="記下客戶回覆、報價內容或下一步；這些文字不會寄給客戶。"
                    maxLength={4000}
                  />
                  <div className="flex justify-end">
                    <Button
                      size="sm"
                      onClick={addNote}
                      disabled={saving || !noteBody.trim()}
                    >
                      加入備註
                    </Button>
                  </div>
                </div>
              )}
              {notes.length === 0 ? (
                <p className="text-sm text-muted-foreground">尚無內部備註</p>
              ) : (
                <div className="space-y-3">
                  {notes.map((note) => (
                    <div
                      key={note.id}
                      className="rounded-md border bg-muted/20 p-3"
                    >
                      <p className="whitespace-pre-wrap text-sm">{note.body}</p>
                      <p className="mt-2 text-xs text-muted-foreground">
                        {note.author_name} ·{" "}
                        {new Date(note.created_at).toLocaleString("zh-TW")}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="text-base">處理歷程</CardTitle>
              <Button variant="ghost" size="sm" onClick={load}>
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
                重新整理
              </Button>
            </CardHeader>
            <CardContent>
              {events.length === 0 ? (
                <p className="text-sm text-muted-foreground">尚無處理紀錄</p>
              ) : (
                <ol className="space-y-4 border-l pl-5">
                  {events.map((event) => (
                    <li key={event.id} className="relative">
                      <span className="absolute -left-[25px] top-1 h-2.5 w-2.5 rounded-full border-2 border-background bg-primary" />
                      <p className="text-sm font-medium">
                        {EVENT_LABEL[event.event_type] ?? event.summary}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {event.actor_name ? `${event.actor_name} · ` : ""}
                        {new Date(event.created_at).toLocaleString("zh-TW")}
                      </p>
                    </li>
                  ))}
                </ol>
              )}
            </CardContent>
          </Card>

          <details className="group rounded-lg border bg-card">
            <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-4 font-semibold">
              <span>更多業務與來源資訊</span>
              <ChevronDown className="h-4 w-4 transition-transform group-open:rotate-180" />
            </summary>
            <div className="space-y-5 border-t p-5 text-sm">
              <section>
                <h2 className="mb-3 font-semibold">採購條件</h2>
                <dl className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  {[
                    ["貿易條件", rfq.incoterm],
                    ["年採購量", rfq.annual_volume],
                    ["目標價格", rfq.target_price],
                    [
                      "是否試單",
                      rfq.is_trial_order == null
                        ? null
                        : rfq.is_trial_order
                          ? "是"
                          : "否",
                    ],
                  ].map(([label, value]) => (
                    <div key={String(label)}>
                      <dt className="text-xs text-muted-foreground">
                        {String(label)}
                      </dt>
                      <dd className="font-medium">{displayValue(value)}</dd>
                    </div>
                  ))}
                </dl>
                {(rfq.required_certs?.length ?? 0) > 0 && (
                  <p className="mt-3">
                    需求認證：{rfq.required_certs?.join("、")}
                  </p>
                )}
              </section>
              <section>
                <h2 className="mb-2 font-semibold">如何找到我們</h2>
                <p>來源頁：{rfq.source_page || "未記錄"}</p>
                <p className="text-muted-foreground">
                  詢價完整度：{rfq.quality_score ?? 0} 分
                </p>
                {(rfq.quality_reasons?.length ?? 0) > 0 && (
                  <ul className="mt-2 list-inside list-disc text-muted-foreground">
                    {rfq.quality_reasons?.map((reason) => (
                      <li key={reason}>{reason}</li>
                    ))}
                  </ul>
                )}
              </section>
              <section>
                <h2 className="mb-2 font-semibold">近期網站行為</h2>
                {rfq.visitor_history.length === 0 ? (
                  <p className="text-muted-foreground">沒有可顯示的訪客歷程</p>
                ) : (
                  <ul className="space-y-2">
                    {rfq.visitor_history.slice(0, 10).map((event, index) => (
                      <li
                        key={`${event.timestamp}-${index}`}
                        className="flex flex-wrap justify-between gap-2 rounded border px-3 py-2"
                      >
                        <span>
                          {event.event_name}
                          {event.page_url ? ` · ${event.page_url}` : ""}
                        </span>
                        <time className="text-xs text-muted-foreground">
                          {new Date(event.timestamp).toLocaleString("zh-TW")}
                        </time>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
              {isManager && rfq.duplicate_candidates.length > 0 && (
                <section>
                  <h2 className="mb-2 font-semibold">可能重複詢價</h2>
                  <div className="space-y-2">
                    {rfq.duplicate_candidates.map((candidate) => (
                      <div
                        key={candidate.id}
                        className="flex items-center justify-between rounded border p-3"
                      >
                        <div>
                          <Link
                            className="font-mono text-primary hover:underline"
                            href={`/dashboard/rfqs/${candidate.id}`}
                          >
                            {candidate.rfq_number}
                          </Link>
                          <p className="text-xs text-muted-foreground">
                            {STATUS_LABEL[candidate.status] ?? candidate.status}{" "}
                            ·{" "}
                            {new Date(candidate.created_at).toLocaleDateString(
                              "zh-TW",
                            )}
                          </p>
                        </div>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => mergeDuplicate(candidate)}
                          disabled={saving}
                        >
                          確認合併
                        </Button>
                      </div>
                    ))}
                  </div>
                </section>
              )}
              {canOperate && (
                <section className="rounded-md border border-red-200 bg-red-50/40 p-4">
                  <h2 className="font-semibold text-red-800">垃圾詢價處理</h2>
                  {!rfq.is_spam && (
                    <Input
                      className="mt-3"
                      value={spamReason}
                      onChange={(event) => setSpamReason(event.target.value)}
                      placeholder="原因，例如：廣告推銷、無效聯絡資料"
                    />
                  )}
                  <Button
                    className="mt-3"
                    variant="outline"
                    size="sm"
                    onClick={toggleSpam}
                    disabled={saving}
                  >
                    {rfq.is_spam ? "還原為一般詢價" : "移至垃圾隔離區"}
                  </Button>
                </section>
              )}
            </div>
          </details>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-5 lg:self-start">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">案件下一步</CardTitle>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="case-status">目前階段</Label>
                <select
                  id="case-status"
                  className={SELECT_CLS}
                  value={status}
                  onChange={(event) => setStatus(event.target.value)}
                  disabled={!canOperate}
                >
                  {Object.entries(STATUS_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              {isClosedChoice && (
                <div className="space-y-3 rounded-md border bg-muted/25 p-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="close-reason">
                      {status === "won" ? "成交原因" : "未成交原因"}
                    </Label>
                    <Input
                      id="close-reason"
                      value={closeReason}
                      onChange={(event) => setCloseReason(event.target.value)}
                      placeholder={
                        status === "won"
                          ? "例如：品質與交期符合需求"
                          : "例如：價格、交期或專案取消"
                      }
                    />
                  </div>
                  {status === "won" && (
                    <>
                      <div className="space-y-1.5">
                        <Label htmlFor="deal-amount">成交金額</Label>
                        <Input
                          id="deal-amount"
                          type="number"
                          min="0"
                          step="0.01"
                          value={dealAmount}
                          onChange={(event) =>
                            setDealAmount(event.target.value)
                          }
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="deal-currency">幣別</Label>
                        <select
                          id="deal-currency"
                          className={SELECT_CLS}
                          value={dealCurrency}
                          onChange={(event) =>
                            setDealCurrency(event.target.value)
                          }
                        >
                          {["USD", "EUR", "TWD", "JPY", "CNY"].map(
                            (currency) => (
                              <option key={currency}>{currency}</option>
                            ),
                          )}
                        </select>
                      </div>
                    </>
                  )}
                </div>
              )}
              {canOperate && (
                <Button
                  className="w-full"
                  onClick={saveStatus}
                  disabled={
                    saving || (status === rfq.status && !isClosedChoice)
                  }
                >
                  {saving ? "儲存中…" : "更新案件階段"}
                </Button>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <UserRound className="h-4 w-4" />
                負責業務
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {isManager ? (
                <>
                  <select
                    className={SELECT_CLS}
                    value={ownerId}
                    onChange={(event) => setOwnerId(event.target.value)}
                  >
                    <option value="">請選擇負責業務</option>
                    {team.map((member) => (
                      <option key={member.id} value={member.id}>
                        {member.full_name}
                      </option>
                    ))}
                  </select>
                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={saveOwner}
                    disabled={saving || !ownerId || ownerId === rfq.assigned_to}
                  >
                    儲存負責人
                  </Button>
                </>
              ) : (
                <p className="text-sm font-medium">
                  {rfq.assigned_to_name || "尚未分派"}
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CalendarClock className="h-4 w-4" />
                下次跟進
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Input
                type="datetime-local"
                value={nextFollowUp}
                onInput={(event) => setNextFollowUp(event.currentTarget.value)}
                onChange={(event) => setNextFollowUp(event.target.value)}
                disabled={!canOperate}
              />
              {canOperate && (
                <Button
                  className="w-full"
                  variant="outline"
                  onClick={saveFollowUp}
                  disabled={
                    saving ||
                    nextFollowUp === toLocalInput(rfq.next_follow_up_at)
                  }
                >
                  儲存跟進時間
                </Button>
              )}
              <p className="text-xs text-muted-foreground">
                設定後會出現在「今日待辦」與逾期提醒中。
              </p>
            </CardContent>
          </Card>

          {(rfq.won_reason || rfq.lost_reason || rfq.deal_amount) && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">結案結果</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                {rfq.deal_amount && (
                  <p>
                    <span className="text-muted-foreground">成交金額：</span>
                    <strong>
                      {rfq.deal_currency} {rfq.deal_amount}
                    </strong>
                  </p>
                )}
                <p>
                  <span className="text-muted-foreground">原因：</span>
                  {rfq.won_reason || rfq.lost_reason}
                </p>
              </CardContent>
            </Card>
          )}
        </aside>
      </div>
    </div>
  );
}
