"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { RefreshCw, CheckCircle2, XCircle, Webhook, BarChart2, Link2, Mail, Megaphone } from "lucide-react";
import { API_BASE, buildApiHeaders } from "@/lib/api/client";

type WebhookEndpoint = { url: string; events?: string[] };
type IntegrationStatus = {
  ga4?: { configured: boolean; measurement_id?: string };
  hubspot?: { configured: boolean };
  google_ads?: { configured: boolean; customer_id?: string };
  meta?: { configured: boolean; pixel_id?: string };
  webhook?: { configured: boolean; endpoint_count?: number; endpoints?: WebhookEndpoint[]; signing_enabled?: boolean };
  smtp?: { configured: boolean; host?: string };
};

const INTEGRATIONS = [
  { key: "ga4" as const, label: "Google Analytics 4", icon: BarChart2, desc: "追蹤頁面流量與使用者行為", envKey: "GA4_MEASUREMENT_ID" },
  { key: "hubspot" as const, label: "HubSpot CRM", icon: Link2, desc: "聯絡人與 RFQ 雙向同步", envKey: "HUBSPOT_API_KEY" },
  { key: "google_ads" as const, label: "Google Ads", icon: Megaphone, desc: "轉換追蹤與再行銷受眾", envKey: "GOOGLE_ADS_CUSTOMER_ID" },
  { key: "meta" as const, label: "Meta Pixel", icon: Megaphone, desc: "Facebook / Instagram 廣告像素", envKey: "META_PIXEL_ID" },
  { key: "webhook" as const, label: "Webhook", icon: Webhook, desc: "向外部系統推送事件通知", envKey: "WEBHOOK_ENDPOINT_URL" },
  { key: "smtp" as const, label: "SMTP", icon: Mail, desc: "自訂郵件伺服器發送通知", envKey: "SMTP_HOST" },
];

export default function SettingsIntegrationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";
  const [status, setStatus] = useState<IntegrationStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true); setError(null);
    fetch(`${API_BASE}/admin/integrations/status`, { headers: buildApiHeaders(token) })
      .then(r => r.json()).then(setStatus).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const configuredCount = status
    ? INTEGRATIONS.filter(i => status[i.key]?.configured).length
    : 0;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">整合設定</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">第三方服務整合狀態 — {configuredCount}/{INTEGRATIONS.length} 已配置</p>
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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {INTEGRATIONS.map(intg => {
          const s = status?.[intg.key];
          const configured = s?.configured ?? false;
          const detail =
            intg.key === "ga4" ? (status?.ga4?.measurement_id ?? null)
            : intg.key === "google_ads" ? (status?.google_ads?.customer_id ?? null)
            : intg.key === "meta" ? (status?.meta?.pixel_id ?? null)
            : intg.key === "smtp" ? (status?.smtp?.host ?? null)
            : intg.key === "webhook" ? (status?.webhook?.endpoint_count ? `${status.webhook.endpoint_count} endpoint(s)` : null)
            : null;

          return (
            <Card key={intg.key} className={configured ? "border-green-200/60 bg-green-50/30" : ""}>
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <intg.icon className={`h-4 w-4 ${configured ? "text-green-600" : "text-muted-foreground/50"}`} />
                    {intg.label}
                  </div>
                  {configured
                    ? <Badge className="bg-green-100 text-green-700 text-xs"><CheckCircle2 className="mr-1 h-3 w-3" />已連接</Badge>
                    : <Badge className="bg-gray-100 text-gray-500 text-xs"><XCircle className="mr-1 h-3 w-3" />未配置</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">{intg.desc}</p>
                {detail && <p className="mt-1.5 text-xs font-mono text-foreground/70">{detail}</p>}
                {!configured && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    設定 <code className="rounded bg-muted px-1">{intg.envKey}</code>
                  </p>
                )}
                {intg.key === "webhook" && status?.webhook?.signing_enabled && (
                  <Badge className="mt-2 text-xs bg-blue-100 text-blue-700">Signing 已啟用</Badge>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card className="mt-6">
        <CardHeader><CardTitle className="text-base">如何配置整合</CardTitle></CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>所有整合均透過環境變數配置。修改 <code className="rounded bg-muted px-1.5 text-foreground">.env</code> 後重啟 API 服務即可生效：</p>
          <div className="rounded-md bg-muted p-3 font-mono text-xs space-y-0.5">
            <p>GA4_MEASUREMENT_ID=G-XXXXXXXXXX</p>
            <p>HUBSPOT_API_KEY=pat-eu1-xxxx</p>
            <p>GOOGLE_ADS_CUSTOMER_ID=123-456-7890</p>
            <p>META_PIXEL_ID=123456789</p>
            <p>WEBHOOK_ENDPOINT_URL=https://hooks.example.com/forgebase</p>
            <p>SMTP_HOST=smtp.example.com</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
