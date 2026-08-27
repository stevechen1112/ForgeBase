"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Ban,
  CheckCircle2,
  FilePenLine,
  RefreshCw,
  RotateCcw,
  Save,
  Send,
  XCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { usePlatformAuth } from "@/lib/auth/platform-store";
import {
  platformAdminApi,
  type ContactCandidate,
  type OutreachDraftPolicy,
  type OutreachDeliveryEvent,
  type OutreachDeliveryPolicy,
  type OutreachMessage,
  type TenantSummary,
} from "@/lib/api/platform-admin";

type EditablePolicy = Omit<
  OutreachDraftPolicy,
  "tenant_id" | "updated_by" | "updated_at" | "persisted"
>;
type EditableDeliveryPolicy = Omit<
  OutreachDeliveryPolicy,
  | "tenant_id"
  | "updated_by"
  | "updated_at"
  | "persisted"
  | "readiness"
  | "controlled_auto_reviewed_by"
  | "controlled_auto_reviewed_at"
>;
const EMPTY_POLICY: EditablePolicy = {
  mode: "off",
  lookback_days: 30,
  snapshot_retention_days: 90,
  max_evidence_events: 100,
  allowed_languages: ["en", "zh-TW"],
  policy_version: "outreach-review-v1",
};
const EMPTY_DELIVERY_POLICY: EditableDeliveryPolicy = {
  mode: "off",
  provider_name: "resend",
  timezone: "UTC",
  quiet_hours_enabled: true,
  quiet_start_hour: 20,
  quiet_end_hour: 8,
  daily_send_quota: 10,
  frequency_cap_days: 30,
  unsubscribe_scope: "tenant",
  controlled_auto_opt_in: false,
  controlled_auto_legal_approved: false,
  controlled_auto_allowed_regions: [],
  controlled_auto_allowed_personas: [],
  controlled_auto_allowed_templates: [],
  controlled_auto_review_sample_pct: 100,
};

export default function OutreachReviewPage() {
  const { state } = usePlatformAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [tenants, setTenants] = useState<TenantSummary[]>([]);
  const [tenantId, setTenantId] = useState("");
  const [policy, setPolicy] = useState<EditablePolicy>(EMPTY_POLICY);
  const [deliveryPolicy, setDeliveryPolicy] = useState<EditableDeliveryPolicy>(
    EMPTY_DELIVERY_POLICY,
  );
  const [deliveryReady, setDeliveryReady] = useState(false);
  const [messages, setMessages] = useState<OutreachMessage[]>([]);
  const [events, setEvents] = useState<Record<string, OutreachDeliveryEvent[]>>(
    {},
  );
  const [candidates, setCandidates] = useState<ContactCandidate[]>([]);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (!token) return;
    void platformAdminApi
      .tenants(token, { is_active: true, limit: 200 })
      .then((rows) => {
        setTenants(rows);
        setTenantId((current) => current || rows[0]?.id || "");
      })
      .catch((cause) =>
        setError(cause instanceof Error ? cause.message : "無法載入租戶。"),
      );
  }, [token]);

  const load = useCallback(async () => {
    if (!token || !tenantId) return;
    setError("");
    try {
      const [nextPolicy, nextDeliveryPolicy, draftRows, candidateRows] =
        await Promise.all([
          platformAdminApi.outreachDraftPolicy(token, tenantId),
          platformAdminApi.outreachDeliveryPolicy(token, tenantId),
          platformAdminApi.outreachMessages(token, tenantId),
          platformAdminApi.contactCandidates(token, tenantId, { limit: 100 }),
        ]);
      const {
        tenant_id: _tenantId,
        updated_by: _updatedBy,
        updated_at: _updatedAt,
        persisted: _persisted,
        ...editable
      } = nextPolicy;
      const {
        tenant_id: _deliveryTenantId,
        updated_by: _deliveryUpdatedBy,
        updated_at: _deliveryUpdatedAt,
        persisted: _deliveryPersisted,
        readiness,
        controlled_auto_reviewed_by: _autoReviewedBy,
        controlled_auto_reviewed_at: _autoReviewedAt,
        ...editableDelivery
      } = nextDeliveryPolicy;
      void _tenantId;
      void _updatedBy;
      void _updatedAt;
      void _persisted;
      void _deliveryTenantId;
      void _deliveryUpdatedBy;
      void _deliveryUpdatedAt;
      void _deliveryPersisted;
      void _autoReviewedBy;
      void _autoReviewedAt;
      setPolicy(editable);
      setDeliveryPolicy(editableDelivery);
      setDeliveryReady(readiness.ready);
      setMessages(draftRows.data);
      setCandidates(candidateRows.data);
      setEvents({});
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法載入外聯草稿。");
    }
  }, [tenantId, token]);
  useEffect(() => {
    void load();
  }, [load]);

  async function savePolicy() {
    setBusy("policy");
    setError("");
    try {
      await platformAdminApi.updateOutreachDraftPolicy(token, tenantId, policy);
      setNotice(
        policy.mode === "review_only"
          ? "草稿審核模式已開啟；核准不會寄送。"
          : "外聯草稿功能已關閉。",
      );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存策略。");
    } finally {
      setBusy("");
    }
  }

  async function saveDeliveryPolicy() {
    setBusy("delivery-policy");
    setError("");
    try {
      await platformAdminApi.updateOutreachDeliveryPolicy(
        token,
        tenantId,
        deliveryPolicy,
      );
      setNotice(
        deliveryPolicy.mode === "approval_send"
          ? "APPROVAL_SEND 已啟用；仍須全域開關、租戶權限與逐封人工核准全部通過。"
          : "外聯寄送已於租戶層關閉。",
      );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存寄送政策。");
    } finally {
      setBusy("");
    }
  }

  async function deliveryAction(
    message: OutreachMessage,
    action: "send" | "cancel" | "retry",
  ) {
    if (
      action === "send" &&
      !window.confirm(
        "確認排程寄送此一已核准 revision？寄送前系統仍會重新檢查證據、抑制與頻率限制。",
      )
    )
      return;
    const note = window
      .prompt(
        action === "send" ? "寄送核准備註（可留空）" : "操作原因（可留空）",
      )
      ?.trim();
    setBusy(message.id);
    setError("");
    try {
      if (action === "send")
        await platformAdminApi.sendOutreachMessage(token, message.id, { note });
      else if (action === "cancel")
        await platformAdminApi.cancelOutreachMessage(token, message.id, {
          note,
        });
      else
        await platformAdminApi.retryOutreachMessage(token, message.id, {
          note,
        });
      setNotice(
        action === "send"
          ? "已進入受控寄送佇列。"
          : action === "cancel"
            ? "已取消尚未開始的寄送。"
            : "已使用原冪等鍵重新排程。",
      );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法完成寄送操作。");
    } finally {
      setBusy("");
    }
  }

  async function loadEvents(messageId: string) {
    setBusy(`events-${messageId}`);
    try {
      const result = await platformAdminApi.outreachMessageEvents(
        token,
        messageId,
      );
      setEvents((current) => ({ ...current, [messageId]: result.data }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法載入寄送事件。");
    } finally {
      setBusy("");
    }
  }

  async function enqueue(candidate: ContactCandidate) {
    setBusy(candidate.id);
    setError("");
    try {
      await platformAdminApi.enqueueOutreachDraft(token, candidate.id);
      setNotice(`已排程 ${candidate.full_name} 的旅程快照與草稿。`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法排程草稿。");
    } finally {
      setBusy("");
    }
  }

  async function review(
    message: OutreachMessage,
    decision: "approve" | "reject",
  ) {
    const note =
      decision === "reject"
        ? window.prompt("請輸入拒絕原因")?.trim()
        : window.prompt("核准備註（可留空）")?.trim();
    if (decision === "reject" && !note) return;
    setBusy(message.id);
    setError("");
    try {
      await platformAdminApi.reviewOutreachMessage(token, message.id, {
        decision,
        reason_code: decision === "reject" ? "manual_reject" : undefined,
        note,
      });
      setNotice(
        decision === "approve" ? "草稿已核准，但未排程寄送。" : "草稿已拒絕。",
      );
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法儲存審核。");
    } finally {
      setBusy("");
    }
  }

  async function revise(message: OutreachMessage) {
    const subject = window.prompt("新主旨", message.subject)?.trim();
    if (!subject) return;
    const currentBody = message.text.replace(/\n\n[^\n]+$/, "");
    const body = window
      .prompt("正文（系統會自動附加唯一 CTA）", currentBody)
      ?.trim();
    if (!body) return;
    const note = window.prompt("修改理由")?.trim();
    if (!note) return;
    setBusy(message.id);
    setError("");
    try {
      await platformAdminApi.reviseOutreachMessage(token, message.id, {
        subject,
        body_without_cta: body,
        note,
      });
      setNotice("已建立新 revision；原內容快照未被改寫。");
      await load();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "無法建立 revision。");
    } finally {
      setBusy("");
    }
  }

  const eligible = candidates.filter(
    (row) =>
      ["approved", "converted"].includes(row.status) &&
      row.verification_status === "verified",
  );
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">外聯審核與受控寄送</h1>
          <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
            只使用已發布內容與有效旅程事件；不揭露追蹤細節、不杜撰價格／規格／交期。只有已核准的最新
            revision 能進入受控寄送佇列。
          </p>
        </div>
        <Button variant="outline" onClick={() => void load()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          重新整理
        </Button>
      </div>
      <div className="flex max-w-xl items-center gap-3">
        <Label>租戶</Label>
        <Select value={tenantId} onValueChange={setTenantId}>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {tenants.map((tenant) => (
              <SelectItem key={tenant.id} value={tenant.id}>
                {tenant.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}
      {notice && (
        <div className="rounded-lg border border-emerald-300 bg-emerald-50 p-4 text-sm text-emerald-800">
          {notice}
        </div>
      )}
      {tenantId && (
        <>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>草稿與證據政策</CardTitle>
              <Badge
                variant={policy.mode === "review_only" ? "info" : "secondary"}
              >
                {policy.mode === "review_only" ? "REVIEW ONLY" : "OFF"}
              </Badge>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <div className="space-y-2">
                <Label>模式</Label>
                <Select
                  value={policy.mode}
                  onValueChange={(mode: "off" | "review_only") =>
                    setPolicy({ ...policy, mode })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="off">關閉</SelectItem>
                    <SelectItem value="review_only">只產生與審核</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>旅程回看天數</Label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={policy.lookback_days}
                  onChange={(event) =>
                    setPolicy({
                      ...policy,
                      lookback_days: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>快照保留天數</Label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={policy.snapshot_retention_days}
                  onChange={(event) =>
                    setPolicy({
                      ...policy,
                      snapshot_retention_days: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>最多證據事件</Label>
                <Input
                  type="number"
                  min={1}
                  max={500}
                  value={policy.max_evidence_events}
                  onChange={(event) =>
                    setPolicy({
                      ...policy,
                      max_evidence_events: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className="flex items-end">
                <Button
                  disabled={busy === "policy"}
                  onClick={() => void savePolicy()}
                >
                  <Save className="mr-2 h-4 w-4" />
                  儲存策略
                </Button>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>Controlled Auto 評估資料</CardTitle>
              <Badge variant="secondary">EVALUATION ONLY</Badge>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <div className="space-y-2">
                <Label>租戶明確 opt-in</Label>
                <Select
                  value={deliveryPolicy.controlled_auto_opt_in ? "yes" : "no"}
                  onValueChange={(value) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      controlled_auto_opt_in: value === "yes",
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="no">尚未同意</SelectItem>
                    <SelectItem value="yes">已明確同意評估</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>法遵／用途審查</Label>
                <Select
                  value={
                    deliveryPolicy.controlled_auto_legal_approved ? "yes" : "no"
                  }
                  onValueChange={(value) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      controlled_auto_legal_approved: value === "yes",
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="no">未通過</SelectItem>
                    <SelectItem value="yes">已通過</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              {(
                [
                  [
                    "白名單地區",
                    "controlled_auto_allowed_regions" as const,
                    "US, DE",
                  ],
                  [
                    "白名單 Persona",
                    "controlled_auto_allowed_personas" as const,
                    "procurement, engineering",
                  ],
                  [
                    "白名單模板",
                    "controlled_auto_allowed_templates" as const,
                    "pump-v1, oem-v2",
                  ],
                ] as const
              ).map(([label, key, placeholder]) => (
                <div key={key} className="space-y-2">
                  <Label>{label}</Label>
                  <Input
                    value={deliveryPolicy[key].join(", ")}
                    placeholder={placeholder}
                    onChange={(event) =>
                      setDeliveryPolicy({
                        ...deliveryPolicy,
                        [key]: event.target.value
                          .split(",")
                          .map((item) => item.trim())
                          .filter(Boolean),
                      })
                    }
                  />
                </div>
              ))}
              <div className="space-y-2">
                <Label>持續人工抽查比例（%）</Label>
                <Input
                  type="number"
                  min={1}
                  max={100}
                  value={deliveryPolicy.controlled_auto_review_sample_pct}
                  onChange={(event) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      controlled_auto_review_sample_pct: Number(
                        event.target.value,
                      ),
                    })
                  }
                />
              </div>
              <div className="flex items-end md:col-span-2 xl:col-span-3">
                <p className="text-xs text-muted-foreground">
                  這些欄位只供 readiness Gate 使用；即使全部通過，系統仍只允許
                  APPROVAL_SEND，不會自動核准或寄送。
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle>APPROVAL_SEND 寄送政策</CardTitle>
              <div className="flex gap-2">
                <Badge variant={deliveryReady ? "success" : "destructive"}>
                  {deliveryReady ? "PLATFORM READY" : "PLATFORM BLOCKED"}
                </Badge>
                <Badge
                  variant={
                    deliveryPolicy.mode === "approval_send"
                      ? "success"
                      : "secondary"
                  }
                >
                  {deliveryPolicy.mode === "approval_send"
                    ? "APPROVAL_SEND"
                    : "OFF"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
              <div className="space-y-2">
                <Label>模式</Label>
                <Select
                  value={deliveryPolicy.mode}
                  onValueChange={(mode: "off" | "approval_send") =>
                    setDeliveryPolicy({ ...deliveryPolicy, mode })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="off">關閉</SelectItem>
                    <SelectItem value="approval_send">核准後可寄送</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>時區</Label>
                <Input
                  value={deliveryPolicy.timezone}
                  onChange={(event) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      timezone: event.target.value,
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>每日上限</Label>
                <Input
                  type="number"
                  min={0}
                  value={deliveryPolicy.daily_send_quota}
                  onChange={(event) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      daily_send_quota: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>同窗口間隔天數</Label>
                <Input
                  type="number"
                  min={1}
                  max={365}
                  value={deliveryPolicy.frequency_cap_days}
                  onChange={(event) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      frequency_cap_days: Number(event.target.value),
                    })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label>退訂範圍</Label>
                <Select
                  value={deliveryPolicy.unsubscribe_scope}
                  onValueChange={(unsubscribe_scope: "tenant" | "global") =>
                    setDeliveryPolicy({ ...deliveryPolicy, unsubscribe_scope })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tenant">此租戶</SelectItem>
                    <SelectItem value="global">全平台</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>安靜時段</Label>
                <Select
                  value={deliveryPolicy.quiet_hours_enabled ? "on" : "off"}
                  onValueChange={(value) =>
                    setDeliveryPolicy({
                      ...deliveryPolicy,
                      quiet_hours_enabled: value === "on",
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="on">啟用</SelectItem>
                    <SelectItem value="off">停用</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-2">
                  <Label>開始時</Label>
                  <Input
                    type="number"
                    min={0}
                    max={23}
                    value={deliveryPolicy.quiet_start_hour}
                    onChange={(event) =>
                      setDeliveryPolicy({
                        ...deliveryPolicy,
                        quiet_start_hour: Number(event.target.value),
                      })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label>結束時</Label>
                  <Input
                    type="number"
                    min={0}
                    max={23}
                    value={deliveryPolicy.quiet_end_hour}
                    onChange={(event) =>
                      setDeliveryPolicy({
                        ...deliveryPolicy,
                        quiet_end_hour: Number(event.target.value),
                      })
                    }
                  />
                </div>
              </div>
              <div className="flex items-end">
                <Button
                  disabled={busy === "delivery-policy"}
                  onClick={() => void saveDeliveryPolicy()}
                >
                  <Save className="mr-2 h-4 w-4" />
                  儲存寄送政策
                </Button>
              </div>
              <p className="md:col-span-2 xl:col-span-6 text-xs text-muted-foreground">
                供應商固定 Resend；安靜時段 {deliveryPolicy.quiet_start_hour}
                :00–{deliveryPolicy.quiet_end_hour}:00。租戶政策不能覆蓋平台
                kill switch。
              </p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>可產生草稿的窗口</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-3">
                {eligible.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    沒有已核准且 verified 的窗口。
                  </p>
                ) : (
                  eligible.map((candidate) => (
                    <div
                      key={candidate.id}
                      className="flex items-center gap-3 rounded-lg border p-3"
                    >
                      <div>
                        <p className="font-medium">{candidate.full_name}</p>
                        <p className="text-xs text-muted-foreground">
                          {candidate.company_name} · {candidate.email_masked}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={
                          policy.mode !== "review_only" || busy === candidate.id
                        }
                        onClick={() => void enqueue(candidate)}
                      >
                        <FilePenLine className="mr-1 h-4 w-4" />
                        產生草稿
                      </Button>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>版本化審核與寄送佇列</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {messages.length === 0 ? (
                <p className="py-8 text-center text-sm text-muted-foreground">
                  目前沒有草稿。
                </p>
              ) : (
                messages.map((message) => (
                  <div key={message.id} className="rounded-lg border p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold">{message.subject}</p>
                        <p className="text-xs text-muted-foreground">
                          {message.to_email_masked} · revision{" "}
                          {message.revision_no} · {message.generation_model} ·
                          嘗試 {message.send_attempts}
                        </p>
                      </div>
                      <Badge
                        variant={
                          [
                            "approved",
                            "delivered",
                            "opened",
                            "clicked",
                          ].includes(message.status)
                            ? "success"
                            : [
                                  "rejected",
                                  "failed",
                                  "bounced",
                                  "complained",
                                  "unsubscribed",
                                ].includes(message.status)
                              ? "destructive"
                              : "outline"
                        }
                      >
                        {message.status}
                      </Badge>
                    </div>
                    <Textarea
                      className="mt-3 min-h-36"
                      readOnly
                      value={message.text}
                    />
                    <div className="mt-3 rounded-md bg-muted p-3 text-xs">
                      <p className="font-medium">證據摘要</p>
                      <p>{message.journey_snapshot?.summary}</p>
                      <p className="mt-1 text-muted-foreground">
                        已發布知識：
                        {message.journey_snapshot?.knowledge_references
                          .map((item) => item.title)
                          .join("、") || "無"}{" "}
                        · 事件{" "}
                        {message.journey_snapshot?.evidence_event_ids.length ??
                          0}{" "}
                        筆
                      </p>
                      {message.last_error && (
                        <p className="mt-2 text-destructive">
                          {message.last_error}
                        </p>
                      )}
                    </div>
                    <div className="mt-3 flex flex-wrap justify-end gap-2">
                      {message.status === "pending_review" && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy === message.id}
                            onClick={() => void revise(message)}
                          >
                            <FilePenLine className="mr-1 h-4 w-4" />
                            建立 revision
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={busy === message.id}
                            onClick={() => void review(message, "reject")}
                          >
                            <XCircle className="mr-1 h-4 w-4" />
                            拒絕
                          </Button>
                          <Button
                            size="sm"
                            disabled={busy === message.id}
                            onClick={() => void review(message, "approve")}
                          >
                            <CheckCircle2 className="mr-1 h-4 w-4" />
                            核准
                          </Button>
                        </>
                      )}
                      {message.status === "approved" && (
                        <Button
                          size="sm"
                          disabled={
                            busy === message.id ||
                            deliveryPolicy.mode !== "approval_send" ||
                            !deliveryReady
                          }
                          onClick={() => void deliveryAction(message, "send")}
                        >
                          <Send className="mr-1 h-4 w-4" />
                          排程寄送
                        </Button>
                      )}
                      {message.status === "queued" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy === message.id}
                          onClick={() => void deliveryAction(message, "cancel")}
                        >
                          <Ban className="mr-1 h-4 w-4" />
                          取消
                        </Button>
                      )}
                      {message.status === "failed" && (
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy === message.id}
                          onClick={() => void deliveryAction(message, "retry")}
                        >
                          <RotateCcw className="mr-1 h-4 w-4" />
                          安全重試
                        </Button>
                      )}
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy === `events-${message.id}`}
                        onClick={() => void loadEvents(message.id)}
                      >
                        寄送時間線
                      </Button>
                    </div>
                    {events[message.id] && (
                      <div className="mt-3 border-l pl-4 text-xs">
                        {events[message.id].length === 0 ? (
                          <p className="text-muted-foreground">
                            尚無寄送事件。
                          </p>
                        ) : (
                          events[message.id].map((event) => (
                            <p key={event.id} className="py-1">
                              <span className="font-medium">
                                {event.event_type}
                              </span>{" "}
                              · {event.occurred_at || event.created_at}
                              {event.reason_code
                                ? ` · ${event.reason_code}`
                                : ""}
                            </p>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
