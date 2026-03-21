"use client";
import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@/lib/auth/store";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { CheckCircle2, XCircle, Linkedin, ExternalLink, Eye, EyeOff, Save, Trash2 } from "lucide-react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type CredentialStatus = { key: string; configured: boolean; preview?: string };

function useCredentials(service: string, keys: string[], token: string) {
  const [status, setStatus] = useState<Record<string, boolean>>({});
  const [previews, setPreviews] = useState<Record<string, string>>({});

  const reload = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/admin/integrations/${service}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) return;
      const data: CredentialStatus[] = await res.json();
      const s: Record<string, boolean> = {};
      const p: Record<string, string> = {};
      for (const k of keys) { s[k] = false; }
      for (const item of data) { s[item.key] = item.configured; p[item.key] = item.preview ?? ""; }
      setStatus(s);
      setPreviews(p);
    } catch { /* ignore */ }
  }, [service, token, keys.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (token) reload(); }, [reload, token]);
  return { status, previews, reload };
}

// ── LinkedIn section ─────────────────────────────────────────────────────────

function LinkedInSection({ token }: { token: string }) {
  const keys = ["access_token", "ad_account_id"];
  const { status, previews, reload } = useCredentials("linkedin", keys, token);
  const [values, setValues] = useState({ access_token: "", ad_account_id: "" });
  const [show, setShow] = useState({ access_token: false, ad_account_id: false });
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveOk, setSaveOk] = useState(false);

  const configured = status["access_token"] && status["ad_account_id"];

  const handleSave = async () => {
    setSaving(true); setSaveError(null); setSaveOk(false);
    try {
      const pairs: Array<[string, string]> = [];
      if (values.access_token.trim()) pairs.push(["access_token", values.access_token.trim()]);
      if (values.ad_account_id.trim()) pairs.push(["ad_account_id", values.ad_account_id.trim()]);
      if (!pairs.length) { setSaveError("請至少填寫一個欄位"); return; }

      await Promise.all(pairs.map(([k, v]) =>
        fetch(`${API_BASE}/admin/integrations/linkedin/${k}`, {
          method: "PUT",
          headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
          body: JSON.stringify({ value: v }),
        })
      ));
      setValues({ access_token: "", ad_account_id: "" });
      await reload();
      setSaveOk(true);
      setTimeout(() => setSaveOk(false), 3000);
    } catch (e: unknown) {
      setSaveError(e instanceof Error ? e.message : "儲存失敗");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (key: string) => {
    await fetch(`${API_BASE}/admin/integrations/linkedin/${key}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${token}` },
    });
    await reload();
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Linkedin className="h-5 w-5 text-[#0077B5]" />
            <CardTitle className="text-base">LinkedIn Marketing API</CardTitle>
          </div>
          <Badge className={configured ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}>
            {configured ? "已串接" : "未串接"}
          </Badge>
        </div>
        <CardDescription>
          將高意圖受眾同步至 LinkedIn Campaign Manager，用於投放 Matched Audience 精準廣告
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">

        {/* Current status */}
        <div className="grid gap-2 sm:grid-cols-2">
          {[
            { key: "access_token", label: "Access Token" },
            { key: "ad_account_id", label: "Ad Account ID" },
          ].map(({ key, label }) => (
            <div key={key} className="flex items-center justify-between rounded-md border px-3 py-2">
              <div>
                <p className="text-sm font-medium">{label}</p>
                {status[key] && previews[key] && (
                  <p className="text-xs text-muted-foreground font-mono">{previews[key]}</p>
                )}
              </div>
              <div className="flex items-center gap-2">
                {status[key]
                  ? <CheckCircle2 className="h-4 w-4 text-green-500" />
                  : <XCircle className="h-4 w-4 text-muted-foreground/40" />}
                {status[key] && (
                  <Button variant="ghost" size="sm" className="h-6 w-6 p-0 text-destructive"
                    onClick={() => handleDelete(key)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input form */}
        <div className="rounded-lg border border-dashed p-4 space-y-4">
          <p className="text-sm font-medium">更新憑證</p>
          {[
            { key: "access_token" as const, label: "LinkedIn Access Token", placeholder: "填入新的 Token 以覆蓋現有值" },
            { key: "ad_account_id" as const, label: "Ad Account ID", placeholder: "例：123456789" },
          ].map(({ key, label, placeholder }) => (
            <div key={key} className="space-y-1.5">
              <Label className="text-xs">{label}</Label>
              <div className="relative">
                <Input
                  type={show[key] ? "text" : "password"}
                  placeholder={placeholder}
                  value={values[key]}
                  onChange={e => setValues(v => ({ ...v, [key]: e.target.value }))}
                  className="pr-9 font-mono text-sm"
                />
                <button
                  type="button"
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground"
                  onClick={() => setShow(s => ({ ...s, [key]: !s[key] }))}
                >
                  {show[key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
          ))}
          {saveError && <p className="text-xs text-destructive">{saveError}</p>}
          {saveOk && <p className="text-xs text-green-600">✓ 儲存成功，LinkedIn 同步功能已啟用</p>}
          <Button size="sm" onClick={handleSave} disabled={saving || (!values.access_token && !values.ad_account_id)}>
            <Save className="mr-2 h-4 w-4" />{saving ? "儲存中…" : "儲存"}
          </Button>
        </div>

        {/* How-to guide */}
        <div className="rounded-lg bg-muted/40 px-4 py-3 text-sm space-y-3">
          <p className="font-medium">如何取得這兩個憑證</p>
          <ol className="list-decimal list-inside space-y-2 text-muted-foreground text-xs leading-relaxed">
            <li>
              前往{" "}
              <a href="https://www.linkedin.com/developers/apps" target="_blank" rel="noopener noreferrer"
                className="text-primary underline-offset-2 hover:underline inline-flex items-center gap-0.5">
                LinkedIn Developer Apps <ExternalLink className="h-3 w-3" />
              </a>{" "}
              建立或選擇一個 App
            </li>
            <li>
              在 App 設定的「Auth」頁簽，申請以下 OAuth 2.0 權限（scopes）：
              <code className="ml-1 rounded bg-muted px-1">rw_dmp_segments</code>、
              <code className="ml-1 rounded bg-muted px-1">r_ads</code>
            </li>
            <li>
              完成 OAuth 授權流程後，取得 <strong>Access Token</strong>（有效期 60 天，可用 Refresh Token 更新）
            </li>
            <li>
              前往{" "}
              <a href="https://www.linkedin.com/campaignmanager/" target="_blank" rel="noopener noreferrer"
                className="text-primary underline-offset-2 hover:underline inline-flex items-center gap-0.5">
                Campaign Manager <ExternalLink className="h-3 w-3" />
              </a>{" "}
              → 點選廣告帳戶 → 網址列中的數字即為 <strong>Ad Account ID</strong>
              <br />例：<code className="rounded bg-muted px-1">campaignmanager/accounts/123456789/</code> → ID 為 <code className="rounded bg-muted px-1">123456789</code>
            </li>
          </ol>
          <p className="text-xs text-muted-foreground pt-1">
            儲存後憑證以 AES-256 加密存於資料庫，不以明文保存。
          </p>
        </div>

      </CardContent>
    </Card>
  );
}

// ── Main page ────────────────────────────────────────────────────────────────

export default function IntegrationsPage() {
  const { state } = useAuth();
  const token = state.status === "authenticated" ? state.accessToken : "";

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight">整合設定</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          管理第三方平台的 API 金鑰。憑證經 AES-256 加密後儲存於資料庫，未來支援多租戶時可依各組織獨立設定。
        </p>
      </div>

      <Alert className="mb-6 border-blue-200 bg-blue-50 text-blue-900">
        <AlertDescription className="text-xs">
          <span className="font-semibold">僅伺服器管理員可見。</span>{" "}
          這些設定直接影響後端服務行為。在 SaaS 模式下，每個租戶的憑證彼此隔離，不會互相影響。
        </AlertDescription>
      </Alert>

      <div className="space-y-6">
        <LinkedInSection token={token} />
      </div>
    </div>
  );
}
