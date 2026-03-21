"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RefreshCw, Mail, CheckCircle2, XCircle, Send, UploadCloud } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

// Matches actual /esp/status response
type ESPStatus = {
  active_provider: string;
  resend_configured: boolean;
  sendgrid_configured: boolean;
  mailchimp_configured: boolean;
  from_email: string;
  from_name: string;
};

type ProviderStats = {
  member_count?: number;
  subscriber_count?: number;
  unsubscribed_count?: number;
  [key: string]: unknown;
};

const PROVIDERS = [
  {
    key: "resend",
    label: "Resend",
    fieldKey: "resend_configured" as const,
    desc: "Transactional 郵件（目前支援作為 active provider）",
    canSyncContacts: false,
    statsEndpoint: null,
  },
  {
    key: "sendgrid",
    label: "SendGrid",
    fieldKey: "sendgrid_configured" as const,
    desc: "Transactional + 行銷郵件，支援聯絡人清單同步",
    canSyncContacts: true,
    syncEndpoint: "/esp/sendgrid/sync-contacts",
    statsEndpoint: "/esp/sendgrid/stats",
  },
  {
    key: "mailchimp",
    label: "Mailchimp",
    fieldKey: "mailchimp_configured" as const,
    desc: "行銷自動化 & 電子報，支援聯絡人清單同步",
    canSyncContacts: true,
    syncEndpoint: "/esp/mailchimp/sync-contacts",
    statsEndpoint: "/esp/mailchimp/stats",
  },
] as const;

/* ── Test Email Dialog ────────────────────────────── */
function TestEmailDialog({ token }: { token: string }) {
  const [open, setOpen] = useState(false);
  const [to, setTo] = useState("");
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function send() {
    if (!to.trim()) return;
    setSending(true); setMsg(null);
    try {
      const r = await fetch(`${API_BASE}/esp/test-email`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ to: to.trim() }),
      });
      if (!r.ok) throw new Error((await r.json()).detail ?? r.statusText);
      setMsg({ ok: true, text: "測試信已發送，請至收件匣確認" });
    } catch (e: unknown) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : "發送失敗" });
    } finally { setSending(false); }
  }

  return (
    <Dialog open={open} onOpenChange={v => { setOpen(v); if (!v) { setMsg(null); setTo(""); } }}>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <Send className="mr-2 h-4 w-4" />發送測試信
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader><DialogTitle>發送測試信</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          {msg && (
            <Alert variant={msg.ok ? "default" : "destructive"}>
              <AlertDescription>{msg.text}</AlertDescription>
            </Alert>
          )}
          <div className="space-y-1">
            <Label>收件地址</Label>
            <Input
              type="email"
              placeholder="your@email.com"
              value={to}
              onChange={e => setTo(e.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={send} disabled={sending || !to.trim()}>
              {sending ? "發送中…" : "發送"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ── Sync Button ──────────────────────────────────── */
function SyncButton({
  token,
  endpoint,
  label,
}: {
  token: string;
  endpoint: string;
  label: string;
}) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function doSync() {
    setSyncing(true); setResult(null);
    try {
      const r = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? r.statusText);
      setResult(`完成：成功 ${data.success}，失敗 ${data.failed}，共 ${data.total} 筆`);
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "同步失敗");
    } finally { setSyncing(false); }
  }

  return (
    <div className="mt-3 space-y-1">
      <Button size="sm" variant="outline" onClick={doSync} disabled={syncing} className="w-full">
        <UploadCloud className="mr-2 h-4 w-4" />
        {syncing ? "同步中…" : label}
      </Button>
      {result && <p className="text-xs text-muted-foreground">{result}</p>}
    </div>
  );
}

/* ── Provider Stats ───────────────────────────────── */
function ProviderStats({ token, endpoint }: { token: string; endpoint: string }) {
  const [stats, setStats] = useState<ProviderStats | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}${endpoint}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.ok ? r.json() : null)
      .then(d => d && setStats(d))
      .catch(() => null);
  }, [token, endpoint]);

  if (!stats) return null;

  const memberCount = stats.member_count ?? stats.subscriber_count;
  const unsubCount = stats.unsubscribed_count;

  if (memberCount === undefined) return null;

  return (
    <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
      <span>訂閱人數：<strong className="text-foreground">{memberCount.toLocaleString()}</strong></span>
      {unsubCount !== undefined && (
        <span>退訂：<strong className="text-foreground">{unsubCount.toLocaleString()}</strong></span>
      )}
    </div>
  );
}

/* ── Main Page ────────────────────────────────────── */
export default function EspPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [espStatus, setEspStatus] = useState<ESPStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/esp/status`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => r.json()).then(setEspStatus).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">ESP 設定</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">電子郵件服務商配置與發送狀態監控</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`} />重新整理
          </Button>
          <TestEmailDialog token={token} />
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {espStatus?.active_provider && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
          <Mail className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-medium">目前啟用供應商</p>
            <p className="text-xs text-muted-foreground">
              <span className="font-semibold capitalize text-foreground">{espStatus.active_provider}</span>
              {espStatus.from_email && (
                <> — 發件人：{espStatus.from_name} &lt;{espStatus.from_email}&gt;</>
              )}
            </p>
          </div>
          <Badge className="ml-auto bg-green-100 text-green-700">已啟用</Badge>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {PROVIDERS.map(p => {
          const isConfigured = espStatus?.[p.fieldKey] ?? false;
          const isActive = espStatus?.active_provider === p.key;
          return (
            <Card key={p.key} className={isActive ? "border-primary/50 bg-primary/5" : ""}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {isConfigured
                      ? <CheckCircle2 className="h-5 w-5 shrink-0 text-green-500" />
                      : <XCircle className="h-5 w-5 shrink-0 text-muted-foreground/40" />}
                    <div>
                      <p className="font-semibold">{p.label}</p>
                      <p className="text-xs text-muted-foreground">{p.desc}</p>
                    </div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <Badge className={isConfigured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                      {isConfigured ? "已配置" : "未配置"}
                    </Badge>
                    {isActive && <Badge className="bg-blue-100 text-blue-700">使用中</Badge>}
                  </div>
                </div>

                {/* Stats for configured providers */}
                {isConfigured && p.statsEndpoint && (
                  <ProviderStats token={token} endpoint={p.statsEndpoint} />
                )}

                {/* Sync button for providers that support contact list */}
                {isConfigured && p.canSyncContacts && p.syncEndpoint && (
                  <SyncButton
                    token={token}
                    endpoint={p.syncEndpoint}
                    label={`同步聯絡人至 ${p.label}`}
                  />
                )}

                {!isConfigured && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    設定環境變數後重啟服務即可啟用
                  </p>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">環境變數配置說明</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>在 <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">.env</code> 中設定以下變數：</p>
          <ul className="list-inside list-disc space-y-1 pl-2">
            <li><code className="text-foreground">ESP_PROVIDER</code> — <code className="text-foreground">"resend"</code> 或 <code className="text-foreground">"sendgrid"</code>（決定寄信用哪個）</li>
            <li><code className="text-foreground">RESEND_API_KEY</code> — Resend 郵件服務</li>
            <li><code className="text-foreground">SENDGRID_API_KEY</code> + <code className="text-foreground">SENDGRID_LIST_ID</code></li>
            <li><code className="text-foreground">MAILCHIMP_API_KEY</code> + <code className="text-foreground">MAILCHIMP_AUDIENCE_ID</code></li>
            <li><code className="text-foreground">EMAIL_FROM</code> + <code className="text-foreground">EMAIL_FROM_NAME</code> — 發件人地址與名稱</li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}


