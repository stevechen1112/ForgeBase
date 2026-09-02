"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, ArrowLeft, CheckCircle2, Clock3, MailCheck, MessageSquareText, UserCheck } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { apiClient } from "@/lib/api/client";
import { authApi, type TeamMember } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

type Status = "new" | "assigned" | "accepted" | "archived";
type RFQDetail = {
  id: string; rfq_number: string; status: Status; priority: string;
  assigned_to: string | null; assigned_to_name: string | null;
  acceptance_due_at: string | null; acceptance_sla_breached: boolean;
  acknowledgement_sent_at: string | null; accepted_at: string | null;
  first_verified_response_at: string | null; archived_at: string | null;
  created_at: string; updated_at: string; source_page: string | null; buyer_timezone: string | null;
  is_spam: boolean; spam_reason: string | null; merged_into_rfq_id: string | null;
  incoterm: string | null; annual_volume: number | null; is_trial_order: boolean;
  required_certs: string[]; target_price: string | number | null;
  form_data: Record<string, unknown> | null;
  contact: { full_name: string; company_name: string | null; email: string; phone: string | null; country: string | null; job_title: string | null } | null;
  products: { id: string; name: string; model_number: string | null }[];
  visitor_history: { event_name: string; timestamp: string; page_url: string | null; page_type: string | null; traffic_source: string | null; campaign_id: string | null; locale: string | null }[];
  duplicate_candidates: { id: string; rfq_number: string; status: string; created_at: string }[];
};
type Note = { id: string; body: string; author_name: string; created_at: string };
type TimelineEvent = { id: string; event_type: string; summary: string; actor_name: string | null; created_at: string };

const STATUS_LABEL: Record<Status, string> = { new: "新進詢價", assigned: "已分派・待接手", accepted: "業務已接手", archived: "已封存" };
const EVENT_LABEL: Record<string, string> = {
  created: "收到網站詢價", acknowledgement_sent: "已寄收件確認", assigned: "已分派負責業務",
  accepted: "業務已接手", archived: "案件已封存", status_changed: "承接狀態變更",
  note_added: "新增內部備註", spam_marked: "移至垃圾隔離區", spam_restored: "從垃圾隔離區還原",
  duplicate_merged: "合併重複詢價", merged_into: "已合併至其他詢價",
};
const PRIORITY_LABEL: Record<string, string> = { low: "低", normal: "一般", high: "高", urgent: "緊急" };

function formatDate(value: string | null) {
  if (!value) return "尚未發生";
  return new Date(value).toLocaleString("zh-TW", { year: "numeric", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit" });
}
function textValue(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "是" : "否";
  if (Array.isArray(value)) return value.join("、") || "—";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}
function fieldLabel(key: string) {
  const labels: Record<string, string> = {
    message: "需求說明", quantity: "需求數量", specifications: "規格", spec: "規格", material: "材質",
    application: "應用", delivery_date: "期望交期", target_date: "期望交期", timeline: "需求時程", drawing_url: "圖面／附件",
    incoterm: "貿易條件", annual_volume: "年需求量", target_price: "目標價格", required_certs: "所需認證",
  };
  return labels[key] || key.replaceAll("_", " ");
}

export default function RFQDetailPage() {
  const params = useParams<{ id: string }>();
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const isManager = user?.role === "owner" || user?.role === "admin";
  const [rfq, setRfq] = useState<RFQDetail | null>(null);
  const [notes, setNotes] = useState<Note[]>([]);
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [assignee, setAssignee] = useState("");
  const [priority, setPriority] = useState("normal");
  const [note, setNote] = useState("");
  const [spamReason, setSpamReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token || !params.id) return;
    setLoading(true); setError(null);
    try {
      const [detail, noteRows, eventRows] = await Promise.all([
        apiClient.get<RFQDetail>(`/tracking/rfqs/${params.id}`, token),
        apiClient.get<Note[]>(`/tracking/rfqs/${params.id}/notes`, token),
        apiClient.get<TimelineEvent[]>(`/tracking/rfqs/${params.id}/events`, token),
      ]);
      setRfq(detail); setNotes(noteRows); setEvents(eventRows);
      setAssignee(detail.assigned_to || ""); setPriority(detail.priority || "normal");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "詢價資料載入失敗"); }
    finally { setLoading(false); }
  }, [params.id, token]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    if (!token || !isManager) return;
    authApi.listTeam(token).then((members) => setTeam(members.filter((member) => member.is_active && ["sales", "admin", "owner"].includes(member.role)))).catch(() => setTeam([]));
  }, [isManager, token]);

  const formFields = useMemo(() => Object.entries(rfq?.form_data || {}).filter(([key]) => !["email", "full_name", "company_name", "phone", "country", "products"].includes(key)), [rfq?.form_data]);

  async function runAction(action: () => Promise<unknown>, success: string) {
    setSaving(true); setError(null); setMessage(null);
    try { await action(); setMessage(success); await load(); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "操作失敗"); }
    finally { setSaving(false); }
  }

  if (loading && !rfq) return <div className="py-20 text-center text-sm text-muted-foreground">載入詢價內容…</div>;
  if (!rfq) return <Alert variant="destructive"><AlertDescription>{error || "找不到這筆詢價"}</AlertDescription></Alert>;

  const canAccept = Boolean(rfq.assigned_to && rfq.status === "assigned" && (isManager || rfq.assigned_to === user?.id));
  return <div className="space-y-5">
    <div><Button asChild variant="ghost" size="sm" className="mb-2 -ml-3"><Link href="/dashboard/rfqs"><ArrowLeft className="mr-2 h-4 w-4" />返回詢價承接</Link></Button>
      <div className="flex flex-wrap items-start justify-between gap-3"><div><div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-bold">{rfq.rfq_number}</h1><span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">{STATUS_LABEL[rfq.status]}</span>{rfq.priority === "urgent" && <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">緊急</span>}</div><p className="mt-1 text-sm text-muted-foreground">{rfq.contact?.company_name || "未填公司"} · {rfq.contact?.full_name || "未填姓名"} · 收到於 {formatDate(rfq.created_at)}</p></div>
        <div className="flex flex-wrap gap-2">{canAccept && <Button disabled={saving} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/status`, { status: "accepted" }, token), "已確認由業務接手")}>確認接手</Button>}{rfq.status === "accepted" && <Button variant="outline" disabled={saving} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/status`, { status: "archived" }, token), "詢價已封存")}>封存案件</Button>}{rfq.status === "archived" && isManager && <Button variant="outline" disabled={saving || !rfq.assigned_to} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/status`, { status: "assigned" }, token), "已重新開啟為待接手")}>重新開啟</Button>}</div>
      </div>
    </div>
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    {message && <Alert><AlertDescription>{message}</AlertDescription></Alert>}
    {rfq.acceptance_sla_breached && rfq.status === "assigned" && <Alert variant="destructive"><AlertTriangle className="h-4 w-4" /><AlertDescription>這筆詢價已超過接手期限，請立即確認接手；這只代表內部交接逾期，不代表已回覆買家。</AlertDescription></Alert>}

    <div className="grid gap-4 lg:grid-cols-4">
      {[
        [Clock3, "收到詢價", formatDate(rfq.created_at)],
        [MailCheck, "收件確認", formatDate(rfq.acknowledgement_sent_at)],
        [UserCheck, "業務接手", formatDate(rfq.accepted_at)],
        [MessageSquareText, "可驗證人工回覆", formatDate(rfq.first_verified_response_at)],
      ].map(([Icon, label, value]) => <Card key={String(label)}><CardContent className="flex gap-3 p-4"><Icon className="mt-0.5 h-5 w-5 text-primary" /><div><p className="text-xs text-muted-foreground">{String(label)}</p><p className="mt-1 text-sm font-semibold">{String(value)}</p></div></CardContent></Card>)}
    </div>

    <div className="grid gap-5 xl:grid-cols-[1.45fr_1fr]">
      <div className="space-y-5">
        <Card><CardHeader><CardTitle>買家與聯絡資料</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2">
          {[ ["姓名", rfq.contact?.full_name], ["公司", rfq.contact?.company_name], ["職稱", rfq.contact?.job_title], ["國家／地區", rfq.contact?.country], ["Email", rfq.contact?.email], ["電話", rfq.contact?.phone] ].map(([label, value]) => <div key={label || "field"}><p className="text-xs text-muted-foreground">{label}</p><p className="mt-1 break-all font-medium">{value || "—"}</p></div>)}
        </CardContent></Card>

        <Card><CardHeader><CardTitle>詢價需求原文</CardTitle></CardHeader><CardContent className="space-y-5">
          {rfq.products.length > 0 && <div><p className="mb-2 text-xs text-muted-foreground">詢問產品</p><div className="flex flex-wrap gap-2">{rfq.products.map((product) => <span key={product.id} className="rounded-md border bg-muted/40 px-3 py-2 text-sm font-medium">{product.name}{product.model_number ? ` · ${product.model_number}` : ""}</span>)}</div></div>}
          <div className="grid gap-4 sm:grid-cols-2">{[
            ["貿易條件", rfq.incoterm], ["年需求量", rfq.annual_volume], ["是否試單", rfq.is_trial_order], ["目標價格", rfq.target_price], ["所需認證", rfq.required_certs], ["買家時區", rfq.buyer_timezone],
          ].map(([label, value]) => <div key={String(label)}><p className="text-xs text-muted-foreground">{String(label)}</p><p className="mt-1 font-medium">{textValue(value)}</p></div>)}</div>
          {formFields.length > 0 && <div className="border-t pt-4"><p className="mb-3 text-xs font-semibold text-muted-foreground">表單填寫內容</p><div className="grid gap-4 sm:grid-cols-2">{formFields.map(([key, value]) => <div key={key} className={key === "message" || key === "specifications" ? "sm:col-span-2" : ""}><p className="text-xs text-muted-foreground">{fieldLabel(key)}</p><p className="mt-1 whitespace-pre-wrap font-medium">{textValue(value)}</p></div>)}</div></div>}
        </CardContent></Card>

        <Card><CardHeader><CardTitle>來訪來源與網站足跡</CardTitle></CardHeader><CardContent>
          <div className="mb-4 grid gap-3 sm:grid-cols-2"><div><p className="text-xs text-muted-foreground">送出詢價頁面</p><p className="mt-1 break-all text-sm font-medium">{rfq.source_page || "未記錄"}</p></div><div><p className="text-xs text-muted-foreground">最近追蹤事件</p><p className="mt-1 text-sm font-medium">{rfq.visitor_history.length} 筆</p></div></div>
          {rfq.visitor_history.length === 0 ? <p className="rounded-md bg-muted/40 p-4 text-sm text-muted-foreground">這位訪客沒有可連結的第一方網站足跡。</p> : <div className="space-y-2">{rfq.visitor_history.map((item, index) => <div key={`${item.timestamp}-${index}`} className="flex gap-3 rounded-md border p-3"><div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" /><div><p className="text-sm font-medium">{item.event_name} {item.page_type ? `· ${item.page_type}` : ""}</p><p className="mt-1 break-all text-xs text-muted-foreground">{formatDate(item.timestamp)}{item.traffic_source ? ` · 來源 ${item.traffic_source}` : ""}{item.page_url ? ` · ${item.page_url}` : ""}</p></div></div>)}</div>}
        </CardContent></Card>
      </div>

      <div className="space-y-5">
        <Card><CardHeader><CardTitle>承接與分派</CardTitle></CardHeader><CardContent className="space-y-4">
          <div><p className="text-xs text-muted-foreground">目前負責人</p><p className="mt-1 font-semibold">{rfq.assigned_to_name || "尚未分派"}</p></div>
          <div><p className="text-xs text-muted-foreground">接手期限</p><p className={`mt-1 font-semibold ${rfq.acceptance_sla_breached ? "text-red-600" : ""}`}>{formatDate(rfq.acceptance_due_at)}</p></div>
          {isManager && <div className="space-y-3 border-t pt-4"><label className="block text-sm font-medium">分派給</label><select className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={assignee} onChange={(event) => setAssignee(event.target.value)}><option value="">選擇負責業務</option>{team.map((member) => <option key={member.id} value={member.id}>{member.full_name}</option>)}</select><label className="block text-sm font-medium">內部優先度</label><select className="h-10 w-full rounded-md border bg-background px-3 text-sm" value={priority} onChange={(event) => setPriority(event.target.value)}>{Object.entries(PRIORITY_LABEL).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><Button className="w-full" disabled={saving || !assignee} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/assign`, { assigned_to: assignee, priority }, token), "分派已更新；等待負責業務確認接手")}>儲存分派</Button></div>}
        </CardContent></Card>

        <Card><CardHeader><CardTitle>內部備註</CardTitle></CardHeader><CardContent className="space-y-3"><textarea className="min-h-24 w-full rounded-md border bg-background p-3 text-sm" value={note} onChange={(event) => setNote(event.target.value)} placeholder="記錄需交接的規格疑問、附件缺漏或內部判斷；不會寄給買家。" /><Button variant="outline" disabled={saving || !note.trim()} onClick={() => runAction(async () => { await apiClient.post(`/tracking/rfqs/${rfq.id}/notes`, { body: note.trim() }, token); setNote(""); }, "備註已新增")}>新增內部備註</Button>{notes.length === 0 ? <p className="text-sm text-muted-foreground">尚無內部備註</p> : notes.map((item) => <div key={item.id} className="rounded-md bg-muted/40 p-3"><p className="whitespace-pre-wrap text-sm">{item.body}</p><p className="mt-2 text-xs text-muted-foreground">{item.author_name} · {formatDate(item.created_at)}</p></div>)}</CardContent></Card>

        {isManager && rfq.duplicate_candidates.length > 0 && <Card><CardHeader><CardTitle>可能重複的詢價</CardTitle></CardHeader><CardContent className="space-y-2">{rfq.duplicate_candidates.map((item) => <div key={item.id} className="flex items-center justify-between gap-3 rounded-md border p-3"><div><Link href={`/dashboard/rfqs/${item.id}`} className="font-mono text-xs font-semibold text-primary hover:underline">{item.rfq_number}</Link><p className="text-xs text-muted-foreground">{formatDate(item.created_at)}</p></div><Button size="sm" variant="outline" disabled={saving} onClick={() => { if (window.confirm(`確定將 ${item.rfq_number} 合併到目前案件？`)) runAction(() => apiClient.post(`/tracking/rfqs/${rfq.id}/merge`, { duplicate_rfq_id: item.id }, token), "重複詢價已合併"); }}>合併</Button></div>)}</CardContent></Card>}

        <Card><CardHeader><CardTitle>資料整理</CardTitle></CardHeader><CardContent className="space-y-3">{rfq.is_spam ? <><p className="text-sm text-red-600">此詢價已隔離為垃圾資料：{rfq.spam_reason || "未填原因"}</p><Button variant="outline" disabled={saving} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/spam`, { is_spam: false }, token), "詢價已還原")}>還原詢價</Button></> : <><Input value={spamReason} onChange={(event) => setSpamReason(event.target.value)} placeholder="隔離原因（必填）" /><Button variant="outline" disabled={saving || !spamReason.trim()} onClick={() => runAction(() => apiClient.put(`/tracking/rfqs/${rfq.id}/spam`, { is_spam: true, reason: spamReason.trim() }, token), "詢價已移至垃圾隔離區")}>標記為垃圾詢價</Button></>}</CardContent></Card>
      </div>
    </div>

    <Card><CardHeader><CardTitle>系統處理紀錄</CardTitle></CardHeader><CardContent>{events.length === 0 ? <p className="text-sm text-muted-foreground">尚無事件紀錄</p> : <div className="grid gap-3 md:grid-cols-2">{events.map((item) => <div key={item.id} className="flex gap-3 rounded-md border p-3"><CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-primary" /><div><p className="text-sm font-medium">{EVENT_LABEL[item.event_type] || item.summary}</p><p className="mt-1 text-xs text-muted-foreground">{formatDate(item.created_at)}{item.actor_name ? ` · ${item.actor_name}` : " · 系統"}</p></div></div>)}</div>}</CardContent></Card>
  </div>;
}
