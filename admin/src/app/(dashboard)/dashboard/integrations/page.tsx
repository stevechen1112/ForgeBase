"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import {
  CheckCircle2, XCircle, Eye, EyeOff, Save, Trash2,
  Mail, Search, UploadCloud, Send,
} from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

// ── Types ─────────────────────────────────────────────────────────────────────

type CredentialStatus = { key: string; configured: boolean; preview?: string };

type FieldDef = {
  key: string;
  label: string;
  placeholder: string;
  isSecret?: boolean;
  isTextarea?: boolean;
};

type EspStatus = {
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

// ── Field configs (module-level to keep reference stable) ─────────────────────

const RESEND_FIELDS: FieldDef[] = [
  { key: "api_key", label: "API Key", placeholder: "re_xxxxxxxxxxxx", isSecret: true },
];

const SENDGRID_FIELDS: FieldDef[] = [
  { key: "api_key", label: "API Key", placeholder: "SG.xxxxxxxxxxxx", isSecret: true },
  { key: "list_id", label: "Marketing List ID", placeholder: "SendGrid 行銷清單 ID" },
];

const MAILCHIMP_FIELDS: FieldDef[] = [
  { key: "api_key", label: "API Key", placeholder: "xxxxxxxxxxxx-us1", isSecret: true },
  { key: "audience_id", label: "Audience ID", placeholder: "Mailchimp Audience / List ID" },
];

const GSC_FIELDS: FieldDef[] = [
  { key: "site_url", label: "Site URL", placeholder: "https://your-domain.com/" },
  { key: "service_account_key_json", label: "Service Account Key JSON", placeholder: '{"type":"service_account","project_id":"..."}', isTextarea: true },
];

// ── useCredentials hook ────────────────────────────────────────────────────────

function useCredentials(service: string, fields: FieldDef[], token: string) {
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [previews, setPreviews] = useState<Record<string, string>>({});

  const keyStr = fields.map(f => f.key).join(",");

  const reload = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/integrations/${service}`, {
        headers: buildApiHeaders(token),
      });
      if (!res.ok) return;
      const data: CredentialStatus[] = await res.json();
      const s: Record<string, boolean> = {};
      const p: Record<string, string> = {};
      for (const k of keyStr.split(",")) { s[k] = false; }
      for (const item of data) { s[item.key] = item.configured; p[item.key] = item.preview ?? ""; }
      setStatus(s);
      setPreviews(p);
    } catch { /* ignore */ }
  }, [service, token, keyStr]);

  useEffect(() => { if (token) reload(); }, [reload, token]);
  return { status, previews, reload };
}

// ── CredentialForm ─────────────────────────────────────────────────────────────

function CredentialForm({ service, fields, token, status, previews, reload }: {
  service: string;
  fields: FieldDef[];
  token: string;
  status: Record<string, boolean>;
  previews: Record<string, string>;
  reload: () => void;
}) {
  const [values, setValues] = useState<Record<string, string>>(
    Object.fromEntries(fields.map(f => [f.key, ""]))
  );
  const [show, setShow] = useState<Record<string, boolean>>(
    Object.fromEntries(fields.map(f => [f.key, false]))
  );
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const handleSave = async () => {
    const pairs = fields.filter(f => values[f.key].trim()).map(f => [f.key, values[f.key].trim()] as [string, string]);
    if (!pairs.length) { setSaveError("請至少填寫一個欄位"); return; }
    setSaving(true); setSaveError(null); setSaveOk(false);
    try {
      await Promise.all(pairs.map(([k, v]) =>
        fetch(`${API_BASE}/admin/integrations/${service}/${k}`, {
          method: "PUT",
          headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
          body: JSON.stringify({ value: v }),
        })
      ));
      setValues(Object.fromEntries(fields.map(f => [f.key, ""])));
      await reload();
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 3000);
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "儲存失敗");
    } finally { setSaving(false); }
  };

  const handleDelete = async (key: string) => {
    await fetch(`${API_BASE}/admin/integrations/${service}/${key}`, {
      method: "DELETE",
      headers: buildApiHeaders(token),
    });
    await reload();
  };

  const hasAnyValue = fields.some(f => values[f.key].trim());

  return (
    <div className="space-y-4">
      {/* Current status rows */}
      <div className="grid gap-2 sm:grid-cols-2">
        {fields.map(f => (
          <div key={f.key} className="flex items-center justify-between rounded-md border px-3 py-2">
            <div>
              <p className="text-sm font-medium">{f.label}</p>
              {status[f.key] && previews[f.key] && (
                <p className="font-mono text-xs text-muted-foreground">{previews[f.key]}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              {status[f.key]
                ? <CheckCircle2 className="h-4 w-4 text-green-500" />
                : <XCircle className="h-4 w-4 text-muted-foreground/40" />}
              {status[f.key] && (
                <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive"
                  onClick={() => handleDelete(f.key)}>
                  <Trash2 className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Input form */}
      <div className="space-y-4 rounded-lg border border-dashed p-4">
        <p className="text-sm font-medium">更新憑證</p>
        {fields.map(f => (
          <div key={f.key} className="space-y-1.5">
            <Label className="text-xs">{f.label}</Label>
            {f.isTextarea ? (
              <Textarea
                placeholder={f.placeholder}
                value={values[f.key]}
                onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
                rows={4}
                className="font-mono text-xs"
              />
            ) : (
              <div className="relative">
                <Input
                  type={f.isSecret && !show[f.key] ? "password" : "text"}
                  placeholder={f.placeholder}
                  value={values[f.key]}
                  onChange={e => setValues(v => ({ ...v, [f.key]: e.target.value }))}
                  className={`${f.isSecret ? "pr-9" : ""} font-mono text-sm`}
                />
                {f.isSecret && (
                  <button type="button"
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                    onClick={() => setShow(s => ({ ...s, [f.key]: !s[f.key] }))}>
                    {show[f.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                )}
              </div>
            )}
          </div>
        ))}
        {saveError && <p className="text-xs text-destructive">{saveError}</p>}
        {saveOk && <p className="text-xs text-green-600">✓ 憑證已加密儲存</p>}
        <Button size="sm" onClick={handleSave} disabled={saving || !hasAnyValue}>
          <Save className="mr-2 h-4 w-4" />{saving ? "儲存中…" : "儲存"}
        </Button>
      </div>
    </div>
  );
}

// ── SyncButton ────────────────────────────────────────────────────────────────

function SyncButton({ token, endpoint, label }: { token: string; endpoint: string; label: string }) {
  const [syncing, setSyncing] = useState(false);
  const [result, setResult] = useState<string | null>(null);

  async function doSync() {
    setSyncing(true); setResult(null);
    try {
      const r = await fetch(`${API_BASE}${endpoint}`, {
        method: "POST",
        headers: buildApiHeaders(token),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? r.statusText);
      setResult(data.message ?? `完成：成功 ${data.success}，失敗 ${data.failed}，共 ${data.total} 筆`);
    } catch (e: unknown) {
      setResult(e instanceof Error ? e.message : "同步失敗");
    } finally { setSyncing(false); }
  }

  return (
    <div className="space-y-1">
      <Button size="sm" variant="outline" onClick={doSync} disabled={syncing}>
        <UploadCloud className="mr-2 h-4 w-4" />{syncing ? "同步中…" : label}
      </Button>
      {result && <p className="text-xs text-muted-foreground">{result}</p>}
    </div>
  );
}

// ── TestEmailDialog ───────────────────────────────────────────────────────────

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
        headers: buildApiHeaders(token, { "Content-Type": "application/json" }),
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
        <Button size="sm" variant="outline"><Send className="mr-2 h-4 w-4" />發送測試信</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader><DialogTitle>發送測試信</DialogTitle></DialogHeader>
        <div className="space-y-4 py-2">
          {msg && <Alert variant={msg.ok ? "default" : "destructive"}><AlertDescription>{msg.text}</AlertDescription></Alert>}
          <div className="space-y-1">
            <Label>收件地址</Label>
            <Input type="email" placeholder="your@email.com" value={to} onChange={e => setTo(e.target.value)} />
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setOpen(false)}>取消</Button>
            <Button onClick={send} disabled={sending || !to.trim()}>{sending ? "發送中…" : "發送"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ── ProviderStats ─────────────────────────────────────────────────────────────

function ProviderStats({ token, endpoint }: { token: string; endpoint: string }) {
  const [stats, setStats] = useState<ProviderStats | null>(null);
  useEffect(() => {
    fetch(`${API_BASE}${endpoint}`, { headers: buildApiHeaders(token) })
      .then(r => r.ok ? r.json() : null).then(d => d && setStats(d)).catch(() => null);
  }, [token, endpoint]);

  const count = stats?.member_count ?? stats?.subscriber_count;
  if (count === undefined) return null;
  return (
    <p className="text-xs text-muted-foreground">
      訂閱人數：<strong className="text-foreground">{count.toLocaleString()}</strong>
      {stats?.unsubscribed_count !== undefined && (
        <> ｜ 退訂：<strong className="text-foreground">{(stats.unsubscribed_count as number).toLocaleString()}</strong></>
      )}
    </p>
  );
}

// ── Email Section ─────────────────────────────────────────────────────────────

const EMAIL_PROVIDERS = [
  {
    key: "resend",
    service: "resend",
    label: "Resend",
    desc: "交易通知信（可作為主要寄信管道）",
    configuredKey: "resend_configured" as const,
    fields: RESEND_FIELDS,
    statsEndpoint: null,
    syncEndpoint: null,
  },
  {
    key: "sendgrid",
    service: "sendgrid",
    label: "SendGrid",
    desc: "交易通知與行銷清單同步",
    configuredKey: "sendgrid_configured" as const,
    fields: SENDGRID_FIELDS,
    statsEndpoint: "/esp/sendgrid/stats",
    syncEndpoint: "/esp/sendgrid/sync-contacts",
  },
  {
    key: "mailchimp",
    service: "mailchimp",
    label: "Mailchimp",
    desc: "行銷自動化 & 電子報",
    configuredKey: "mailchimp_configured" as const,
    fields: MAILCHIMP_FIELDS,
    statsEndpoint: "/esp/mailchimp/stats",
    syncEndpoint: "/esp/mailchimp/sync-contacts",
  },
] as const;

function EmailProviderSubsection({ token, provider, isActive, isConfigured }: {
  token: string;
  provider: typeof EMAIL_PROVIDERS[number];
  isActive: boolean;
  isConfigured: boolean;
}) {
  const { status, previews, reload } = useCredentials(provider.service, provider.fields as unknown as FieldDef[], token);

  return (
    <div className={`rounded-lg border p-4 ${isActive ? "border-primary/40 bg-primary/5" : ""}`}>
      <div className="mb-4 flex items-start justify-between">
        <div>
          <p className="font-semibold">{provider.label}</p>
          <p className="text-xs text-muted-foreground">{provider.desc}</p>
          {isConfigured && provider.statsEndpoint && (
            <ProviderStats token={token} endpoint={provider.statsEndpoint} />
          )}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Badge className={isConfigured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
            {isConfigured ? "已配置" : "未配置"}
          </Badge>
          {isActive && <Badge className="bg-blue-100 text-blue-700">使用中</Badge>}
        </div>
      </div>
      <CredentialForm
        service={provider.service}
        fields={provider.fields as unknown as FieldDef[]}
        token={token}
        status={status}
        previews={previews}
        reload={reload}
      />
      {isConfigured && provider.syncEndpoint && (
        <div className="mt-4">
          <SyncButton token={token} endpoint={provider.syncEndpoint} label={`同步聯絡人至 ${provider.label}`} />
        </div>
      )}
    </div>
  );
}

function EmailSection({ token }: { token: string }) {
  const [espStatus, setEspStatus] = useState<EspStatus | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/esp/status`, { headers: buildApiHeaders(token) })
      .then(r => r.json()).then(setEspStatus).catch(() => null);
  }, [token]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Mail className="h-5 w-5 text-primary" />
          <CardTitle className="text-base">Email 服務商</CardTitle>
        </div>
        <CardDescription>郵件服務商憑證管理</CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Active provider status */}
        {espStatus && (
          <div className="flex items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
            <div className="flex-1">
              <p className="text-sm font-medium">目前寄信供應商</p>
              <p className="text-xs text-muted-foreground">
                <span className="font-semibold capitalize text-foreground">{espStatus.active_provider}</span>
                {espStatus.from_email && (
                  <> — 發件人：{espStatus.from_name} &lt;{espStatus.from_email}&gt;</>
                )}
              </p>
            </div>
            <TestEmailDialog token={token} />
          </div>
        )}

        <div className="space-y-4">
          {EMAIL_PROVIDERS.map(p => (
            <EmailProviderSubsection
              key={p.key}
              token={token}
              provider={p}
              isActive={espStatus?.active_provider === p.key}
              isConfigured={espStatus?.[p.configuredKey] ?? false}
            />
          ))}
        </div>

        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer font-medium text-foreground/80">環境變數配置說明（展開）</summary>
          <ul className="mt-2 list-inside list-disc space-y-1 pl-2">
            <li><code className="rounded bg-muted px-1 text-foreground">ESP_PROVIDER</code> — <code className="text-foreground">&quot;resend&quot;</code> 或 <code className="text-foreground">&quot;sendgrid&quot;</code>（決定寄信用哪個）</li>
            <li><code className="rounded bg-muted px-1 text-foreground">RESEND_API_KEY</code> — Resend 郵件服務</li>
            <li><code className="rounded bg-muted px-1 text-foreground">SENDGRID_API_KEY</code> + <code className="rounded bg-muted px-1 text-foreground">SENDGRID_LIST_ID</code></li>
            <li><code className="rounded bg-muted px-1 text-foreground">MAILCHIMP_API_KEY</code> + <code className="rounded bg-muted px-1 text-foreground">MAILCHIMP_AUDIENCE_ID</code></li>
            <li><code className="rounded bg-muted px-1 text-foreground">EMAIL_FROM</code> + <code className="rounded bg-muted px-1 text-foreground">EMAIL_FROM_NAME</code> — 發件人地址與名稱</li>
          </ul>
        </details>
      </CardContent>
    </Card>
  );
}

// ── Google Search Console Section ─────────────────────────────────────────────

function GscSection({ token }: { token: string }) {
  const { status, previews, reload } = useCredentials("gsc", GSC_FIELDS, token);
  const configured = GSC_FIELDS.every(f => status[f.key]);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Search className="h-5 w-5 text-[#4285F4]" />
            <CardTitle className="text-base">Google Search Console</CardTitle>
          </div>
          <Badge className={configured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
            {configured ? "已串接" : "未串接"}
          </Badge>
        </div>
        <CardDescription>SEO 診斷所需的 Search Console 爬蟲流量與關鍵字排名數據</CardDescription>
      </CardHeader>
      <CardContent>
        <CredentialForm service="gsc" fields={GSC_FIELDS} token={token}
          status={status} previews={previews} reload={reload} />
      </CardContent>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">整合設定</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          管理第三方服務金鑰（如 Telegram、郵件服務）。金鑰會加密保存。
        </p>
      </div>

      <Alert className="mb-6 border-blue-200 bg-blue-50 text-blue-900">
        <AlertDescription className="text-xs">
          <span className="font-semibold">僅伺服器管理員可見。</span>{" "}
          目前保留 Email 與 Google Search Console 所需設定；憑證會加密儲存在資料庫中。
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <EmailSection token={token} />
        <GscSection token={token} />
      </div>
    </div>
  );
}
