"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ExternalLink, MailCheck, RefreshCw, ShieldAlert } from "lucide-react";

import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";
import { authApi, type TeamMember } from "@/lib/api/auth";
import { useAuth } from "@/lib/auth/store";

type ReplyRow = {
  id: string;
  sender_email_masked: string;
  classification: string;
  classification_confidence: number;
  status: string;
  needs_human_review: boolean;
  attachment_count: number;
  attachments_quarantined: boolean;
  received_at: string;
  fetched_at: string | null;
};

type HandoffRow = {
  id: string;
  inbound_reply_id: string;
  rfq_id: string | null;
  owner_id: string | null;
  status: string;
  priority: string;
  classification: string;
  summary: string;
  sla_due_at: string;
  sla_breached: boolean;
};

type ReplyDetail = ReplyRow & {
  subject: string;
  body_text: string | null;
  attachment_metadata: Array<Record<string, unknown>>;
  processing_error: string | null;
  reply_externally_url: string | null;
  original_outreach: { id: string; subject: string; text: string } | null;
  buyer_context: {
    sender_matches_outreach_recipient: boolean;
    company_name: string | null;
    company_domain: string | null;
    company_confidence: number | null;
    candidate_name: string | null;
    candidate_title: string | null;
    candidate_source_provider: string | null;
    journey_summary: string | null;
    top_products: Array<Record<string, unknown>>;
  };
  thread: ReplyRow[];
};

type ReplyPolicy = {
  mode: "off" | "review_only";
  handoff_sla_hours: number;
  content_retention_days: number;
  route_configured: boolean;
};

const SELECT_CLS =
  "h-10 rounded-md border border-input bg-background px-3 text-sm text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

const CLASSIFICATION_LABEL: Record<string, string> = {
  positive: "正向回覆",
  question: "詢問問題",
  rfq: "詢價意圖",
  not_now: "暫不需要",
  wrong_person: "窗口錯誤",
  unsubscribe: "要求退訂",
  negative: "負向回覆",
  auto_reply: "自動回覆",
  bounce: "退信",
  unknown: "待人工判斷",
};

function formatDate(value: string) {
  return new Date(value).toLocaleString("zh-TW", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function apiFetch<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: buildApiHeaders(token, init?.headers),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail || `HTTP ${response.status}`);
  return data as T;
}

export default function RepliesPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const user = state.status === "authenticated" ? state.user : null;
  const isManager = user?.role === "owner" || user?.role === "admin";
  const canOperate = isManager || user?.role === "sales";
  const [replies, setReplies] = useState<ReplyRow[]>([]);
  const [handoffs, setHandoffs] = useState<HandoffRow[]>([]);
  const [detail, setDetail] = useState<ReplyDetail | null>(null);
  const [policy, setPolicy] = useState<ReplyPolicy | null>(null);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const selectedHandoff = useMemo(
    () => handoffs.find((row) => row.inbound_reply_id === detail?.id) ?? null,
    [detail?.id, handoffs],
  );

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    const query = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : "";
    try {
      const [replyData, handoffData, policyData] = await Promise.all([
        apiFetch<{ items: ReplyRow[] }>(token, `/tracking/replies${query}`),
        apiFetch<{ items: HandoffRow[] }>(token, "/tracking/sales-handoffs"),
        apiFetch<ReplyPolicy>(token, "/tracking/replies/policy"),
      ]);
      setReplies(replyData.items);
      setHandoffs(handoffData.items);
      setPolicy(policyData);
      if (detail && !replyData.items.some((row) => row.id === detail.id)) setDetail(null);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "回信工作台載入失敗");
    } finally {
      setLoading(false);
    }
  }, [detail, statusFilter, token]);

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
            (member) => member.is_active && ["sales", "admin", "owner"].includes(member.role),
          ),
        ),
      )
      .catch(() => setTeam([]));
  }, [isManager, token]);

  async function openReply(id: string) {
    setError(null);
    try {
      setDetail(await apiFetch<ReplyDetail>(token, `/tracking/replies/${id}`));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "回信內容載入失敗");
    }
  }

  async function action(path: string, body: Record<string, unknown> = { note }) {
    setWorking(true);
    setError(null);
    try {
      await apiFetch(token, path, { method: "POST", body: JSON.stringify(body) });
      setNote("");
      await load();
      if (detail) await openReply(detail.id);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "操作失敗");
    } finally {
      setWorking(false);
    }
  }

  async function setPolicyMode(mode: "off" | "review_only") {
    if (!policy) return;
    setWorking(true);
    setError(null);
    try {
      const next = await apiFetch<ReplyPolicy>(token, "/tracking/replies/policy", {
        method: "PUT",
        body: JSON.stringify({ ...policy, mode }),
      });
      setPolicy(next);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "回信政策更新失敗");
    } finally {
      setWorking(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">買家回信與業務接手</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            人工確認回信、停止不適合的後續寄送，並把有效需求交給真人業務或轉成詢價案件。
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
        </Button>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {policy && (
        <Card className="mb-5">
          <CardContent className="flex flex-wrap items-center justify-between gap-4 p-4">
            <div>
              <p className="font-medium">Inbound Reply：{policy.mode === "review_only" ? "人工審核模式" : "關閉"}</p>
              <p className="text-xs text-muted-foreground">
                Reply-To 路由{policy.route_configured ? "已就緒" : "尚未設定"} · 接手 SLA {policy.handoff_sla_hours} 小時 · 內容保存 {policy.content_retention_days} 天
              </p>
            </div>
            {isManager && (
              <Button
                variant={policy.mode === "review_only" ? "outline" : "default"}
                size="sm"
                disabled={working || (!policy.route_configured && policy.mode === "off")}
                onClick={() => setPolicyMode(policy.mode === "review_only" ? "off" : "review_only")}
              >
                {policy.mode === "review_only" ? "關閉收信" : "啟用人工審核"}
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      <div className="mb-4 flex flex-wrap gap-2">
        <select
          className={SELECT_CLS}
          value={statusFilter}
          aria-label="回信狀態"
          onChange={(event) => setStatusFilter(event.target.value)}
        >
          <option value="">全部回信</option>
          <option value="needs_review">待人工判斷</option>
          <option value="handed_off">已建立接手</option>
          <option value="classified">已分類</option>
          <option value="ignored">自動回覆／退信</option>
          <option value="failed">處理失敗</option>
        </select>
        <Input
          className="max-w-md"
          value={note}
          onChange={(event) => setNote(event.target.value)}
          placeholder="本次處理備註（會寫入稽核歷程）"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(380px,0.95fr)]">
        <Card>
          <CardHeader><CardTitle className="text-base">Reply inbox</CardTitle></CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <p className="p-8 text-center text-sm text-muted-foreground">載入回信…</p>
            ) : replies.length === 0 ? (
              <p className="p-8 text-center text-sm text-muted-foreground">目前沒有符合條件的回信</p>
            ) : (
              <div className="divide-y">
                {replies.map((row) => {
                  const handoff = handoffs.find((item) => item.inbound_reply_id === row.id);
                  return (
                    <button
                      key={row.id}
                      type="button"
                      onClick={() => openReply(row.id)}
                      className={`w-full p-4 text-left hover:bg-muted/40 ${detail?.id === row.id ? "bg-muted/60" : ""}`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="font-medium">{row.sender_email_masked}</p>
                          <p className="mt-1 text-xs text-muted-foreground">{formatDate(row.received_at)}</p>
                        </div>
                        <Badge variant={row.needs_human_review ? "destructive" : "secondary"}>
                          {CLASSIFICATION_LABEL[row.classification] ?? row.classification}
                        </Badge>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2 text-xs text-muted-foreground">
                        <span>{Math.round(row.classification_confidence * 100)}% 信心</span>
                        {handoff && <span>· 接手：{handoff.status}</span>}
                        {row.attachments_quarantined && <span>· {row.attachment_count} 個附件已隔離</span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="text-base">回信與接手處理</CardTitle></CardHeader>
          <CardContent>
            {!detail ? (
              <p className="py-12 text-center text-sm text-muted-foreground">請從左側選擇一封回信</p>
            ) : (
              <div className="space-y-5">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge>{CLASSIFICATION_LABEL[detail.classification] ?? detail.classification}</Badge>
                    <span className="text-xs text-muted-foreground">{detail.sender_email_masked}</span>
                  </div>
                  <h2 className="mt-3 font-semibold">{detail.subject || "（無主旨）"}</h2>
                  <div className="mt-3 whitespace-pre-wrap rounded-md border bg-muted/30 p-3 text-sm">
                    {detail.body_text || "尚無可顯示的純文字內容"}
                  </div>
                </div>

                {detail.attachments_quarantined && (
                  <Alert>
                    <ShieldAlert className="h-4 w-4" />
                    <AlertDescription>
                      {detail.attachment_count} 個附件只保存安全中繼資料，未下載或在後台執行。
                    </AlertDescription>
                  </Alert>
                )}

                {detail.original_outreach && (
                  <div className="rounded-md border p-3 text-sm">
                    <p className="font-medium">原始外聯：{detail.original_outreach.subject}</p>
                    <p className="mt-2 line-clamp-5 whitespace-pre-wrap text-muted-foreground">
                      {detail.original_outreach.text}
                    </p>
                  </div>
                )}

                <div className="rounded-md border p-3 text-sm">
                  <p className="font-medium">原外聯候選與旅程依據</p>
                  <p className="mt-1 text-muted-foreground">
                    {detail.buyer_context.company_name || "公司待確認"}
                    {detail.buyer_context.company_domain ? ` · ${detail.buyer_context.company_domain}` : ""}
                    {detail.buyer_context.company_confidence !== null
                      ? ` · 公司信心 ${Math.round(detail.buyer_context.company_confidence * 100)}%`
                      : ""}
                  </p>
                  <p className="mt-1 text-muted-foreground">
                    {detail.buyer_context.candidate_name || "窗口待確認"}
                    {detail.buyer_context.candidate_title ? ` · ${detail.buyer_context.candidate_title}` : ""}
                  </p>
                  {detail.buyer_context.journey_summary && (
                    <p className="mt-2 whitespace-pre-wrap text-muted-foreground">
                      {detail.buyer_context.journey_summary}
                    </p>
                  )}
                  {!detail.buyer_context.sender_matches_outreach_recipient && (
                    <p className="mt-2 font-medium text-amber-700">
                      回信寄件人不同於原外聯收件人；公司與窗口僅是原始外聯脈絡，不代表寄件人身分。
                    </p>
                  )}
                </div>

                {selectedHandoff?.sla_breached && (
                  <Alert variant="destructive">
                    <AlertDescription>此接手已超過 SLA，請立即處理或改派。</AlertDescription>
                  </Alert>
                )}

                <div className="flex flex-wrap gap-2">
                  {isManager && !detail.fetched_at && ["failed", "needs_review"].includes(detail.status) && (
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={working}
                      onClick={() => action(`/tracking/replies/${detail.id}/fetch`)}
                    >
                      重新擷取內容
                    </Button>
                  )}
                  {canOperate && !selectedHandoff && (
                    <Button
                      size="sm"
                      disabled={working}
                      onClick={() => action(`/tracking/replies/${detail.id}/handoff`)}
                    >
                      <MailCheck className="mr-2 h-4 w-4" />建立並接受接手
                    </Button>
                  )}
                  {canOperate && selectedHandoff && selectedHandoff.status === "new" && (
                    <Button size="sm" disabled={working} onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/accept`)}>
                      接受案件
                    </Button>
                  )}
                  {canOperate && selectedHandoff && !["closed", "converted_to_rfq"].includes(selectedHandoff.status) && (
                    <>
                      {detail.reply_externally_url && <Button asChild variant="outline" size="sm">
                        <a
                          href={detail.reply_externally_url}
                          onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/contacted`)}
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />用外部郵件回覆
                        </a>
                      </Button>}
                      <Button size="sm" disabled={working} onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/convert-to-rfq`)}>
                        建立 RFQ
                      </Button>
                      <Button variant="outline" size="sm" disabled={working} onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/wrong-person`)}>
                        錯誤窗口
                      </Button>
                      <Button variant="outline" size="sm" disabled={working} onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/unsubscribe`)}>
                        退訂
                      </Button>
                      <Button variant="ghost" size="sm" disabled={working} onClick={() => action(`/tracking/sales-handoffs/${selectedHandoff.id}/close`)}>
                        結案
                      </Button>
                    </>
                  )}
                </div>

                {isManager && selectedHandoff && !["closed", "converted_to_rfq"].includes(selectedHandoff.status) && (
                  <select
                    className={`${SELECT_CLS} w-full`}
                    value={selectedHandoff.owner_id ?? ""}
                    aria-label="改派業務"
                    onChange={(event) =>
                      event.target.value &&
                      action(`/tracking/sales-handoffs/${selectedHandoff.id}/assign`, {
                        owner_id: event.target.value,
                        note,
                      })
                    }
                  >
                    <option value="">選擇負責業務</option>
                    {team.map((member) => <option key={member.id} value={member.id}>{member.full_name}</option>)}
                  </select>
                )}

                {selectedHandoff?.rfq_id && (
                  <Button asChild variant="outline" className="w-full">
                    <a href={`/dashboard/rfqs/${selectedHandoff.rfq_id}`}>前往 RFQ 案件</a>
                  </Button>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
