"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, Mail, CheckCircle2, XCircle } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type ESPStatus = {
  active_provider?: string;
  resend_configured?: boolean;
  sendgrid_configured?: boolean;
  mailchimp_configured?: boolean;
  smtp_configured?: boolean;
  from_email?: string;
  from_name?: string;
};

const PROVIDERS = [
  { key: "resend", label: "Resend", fieldKey: "resend_configured" as const, desc: "Transactional mail via Resend API" },
  { key: "sendgrid", label: "SendGrid", fieldKey: "sendgrid_configured" as const, desc: "Transactional + marketing mail" },
  { key: "mailchimp", label: "Mailchimp", fieldKey: "mailchimp_configured" as const, desc: "Marketing automation & newsletters" },
  { key: "smtp", label: "SMTP (Custom)", fieldKey: "smtp_configured" as const, desc: "自設 SMTP 伺服器，支援所有穩定配置" },
];

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
          <h1 className="text-2xl font-bold tracking-tight">ESP 郵件設定</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">電子郵件服務商配置與發送狀態監控</p>
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

      {espStatus && espStatus.active_provider && (
        <div className="mb-6 flex items-center gap-3 rounded-lg border bg-muted/30 px-4 py-3">
          <Mail className="h-5 w-5 text-primary" />
          <div>
            <p className="text-sm font-medium">目前啟用供應商</p>
            <p className="text-xs text-muted-foreground">
              <span className="font-semibold text-foreground capitalize">{espStatus.active_provider}</span>
              {espStatus.from_email && ` — 發件人：${espStatus.from_name ?? ""} <${espStatus.from_email}>`}
            </p>
          </div>
          <Badge className="ml-auto bg-green-100 text-green-700">已啟用</Badge>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        {PROVIDERS.map(p => {
          const isConfigured = espStatus?.[p.fieldKey] ?? false;
          const isActive = espStatus?.active_provider === p.key;
          return (
            <Card key={p.key} className={isActive ? "border-primary/50 bg-primary/5" : ""}>
              <CardContent className="pt-4">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    {isConfigured
                      ? <CheckCircle2 className="h-5 w-5 text-green-500" />
                      : <XCircle className="h-5 w-5 text-muted-foreground/40" />}
                    <div>
                      <p className="font-semibold">{p.label}</p>
                      <p className="text-xs text-muted-foreground">{p.desc}</p>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <Badge className={isConfigured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
                      {isConfigured ? "已配置" : "未配置"}
                    </Badge>
                    {isActive && <Badge className="bg-blue-100 text-blue-700">使用中</Badge>}
                  </div>
                </div>
                {!isConfigured && (
                  <p className="mt-3 text-xs text-muted-foreground">
                    請在 <code className="rounded bg-muted px-1">.env</code> 中設定 {p.label.toUpperCase().replace(" ", "_")}_API_KEY 後重啟服務
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
          <p>在 <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">.env</code> 或 <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">api/app/core/config.py</code> 中設定：</p>
          <ul className="list-inside list-disc space-y-1 pl-2">
            <li><code className="text-foreground">RESEND_API_KEY</code> — Resend 郵件服務</li>
            <li><code className="text-foreground">SENDGRID_API_KEY</code> — SendGrid 郵件服務</li>
            <li><code className="text-foreground">MAILCHIMP_API_KEY</code> + <code className="text-foreground">MAILCHIMP_SERVER_PREFIX</code></li>
            <li><code className="text-foreground">SMTP_HOST</code>, <code className="text-foreground">SMTP_PORT</code>, <code className="text-foreground">SMTP_USER</code>, <code className="text-foreground">SMTP_PASSWORD</code></li>
            <li><code className="text-foreground">ESP_FROM_EMAIL</code>, <code className="text-foreground">ESP_FROM_NAME</code></li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
